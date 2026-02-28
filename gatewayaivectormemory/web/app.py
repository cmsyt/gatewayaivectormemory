import sys
import time
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from gatewayaivectormemory.db.connection import ConnectionManager
from gatewayaivectormemory.db.schema import init_db
from gatewayaivectormemory.embedding.engine import EmbeddingEngine

STATIC_DIR = Path(__file__).parent / "static"

_state: dict = {}


def get_state() -> dict:
    return _state


@asynccontextmanager
async def lifespan(app: FastAPI):
    cfg = app.state.config
    cm = ConnectionManager(cfg["pg_url"])
    with cm.get_conn() as conn:
        init_db(conn)
        conn.commit()
    print("[gatewayaivectormemory-web] PostgreSQL connected", file=sys.stderr)

    engine = EmbeddingEngine()
    embed_url = cfg.get("embed_url", "")
    if embed_url:
        import os
        os.environ["EMBEDDING_SERVER_URL"] = embed_url
    try:
        engine.load()
        print(f"[gatewayaivectormemory-web] EmbeddingEngine ready (remote={engine.is_remote})", file=sys.stderr)
    except Exception as e:
        engine = None
        print(f"[gatewayaivectormemory-web] Semantic search disabled: {e}", file=sys.stderr)

    _state["cm"] = cm
    _state["engine"] = engine
    _state["config"] = cfg

    yield
    cm.close()


def create_app(config: dict | None = None) -> FastAPI:
    if config is None:
        import os
        config = {
            "pg_url": os.environ.get("GATEWAYAIVECTORMEMORY_PG_URL", ""),
            "embed_url": os.environ.get("GATEWAYAIVECTORMEMORY_EMBED_URL", ""),
            "user_id": os.environ.get("GATEWAYAIVECTORMEMORY_USER_ID", ""),
            "token": os.environ.get("GATEWAYAIVECTORMEMORY_TOKEN", ""),
        }
    app = FastAPI(title="GatewayAIVectorMemory Web Dashboard", lifespan=lifespan)
    app.state.config = config

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Token 认证中间件
    @app.middleware("http")
    async def auth_middleware(request: Request, call_next):
        token = get_state().get("config", {}).get("token", "")
        if not token:
            return await call_next(request)
        # 静态文件和健康检查不需要认证
        path = request.url.path
        if path == "/api/health" or not path.startswith("/api/"):
            return await call_next(request)
        # 检查 Authorization header 或 query param
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer ") and auth_header[7:] == token:
            return await call_next(request)
        from urllib.parse import parse_qs
        q_token = parse_qs(str(request.url.query)).get("token", [None])[0]
        if q_token == token:
            return await call_next(request)
        return JSONResponse({"detail": "Unauthorized"}, status_code=401)

    # 请求日志中间件
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        start = time.time()
        response: Response = await call_next(request)
        latency = (time.time() - start) * 1000
        if request.url.path.startswith("/api/"):
            print(
                f"[gatewayaivectormemory-web] {request.method} {request.url.path} "
                f"status={response.status_code} {latency:.0f}ms",
                file=sys.stderr,
            )
        return response

    # API 路由
    from gatewayaivectormemory.web.api import register_routes
    register_routes(app)

    # 健康检查
    @app.get("/api/health")
    async def health():
        st = get_state()
        pg_ok = False
        try:
            cm: ConnectionManager = st["cm"]
            with cm.get_conn() as conn:
                conn.execute("SELECT 1")
            pg_ok = True
        except Exception:
            pass
        return {"status": "ok" if pg_ok else "degraded", "postgresql": pg_ok}

    # 静态文件服务（放在最后，作为 fallback）
    @app.get("/{path:path}")
    async def serve_static(path: str):
        file_path = STATIC_DIR / (path or "index.html")
        if not file_path.exists() or not file_path.is_file():
            file_path = STATIC_DIR / "index.html"
        if not file_path.exists():
            return JSONResponse({"detail": "Not Found"}, status_code=404)
        content_types = {
            ".html": "text/html; charset=utf-8",
            ".css": "text/css; charset=utf-8",
            ".js": "application/javascript; charset=utf-8",
            ".json": "application/json",
            ".svg": "image/svg+xml",
            ".png": "image/png",
        }
        ct = content_types.get(file_path.suffix, "application/octet-stream")
        return FileResponse(file_path, media_type=ct)

    return app


def run_web(pg_url: str = "", port: int = 9080, bind: str = "127.0.0.1",
            token: str | None = None, quiet: bool = False, daemon: bool = False,
            user_id: str = "", embed_url: str = "",
            project_dir: str | None = None):
    import os
    if not pg_url:
        pg_url = os.environ.get("GATEWAYAIVECTORMEMORY_PG_URL", "")
    if not pg_url:
        print("Error: --pg-url or GATEWAYAIVECTORMEMORY_PG_URL is required", file=sys.stderr)
        sys.exit(1)

    config = {
        "pg_url": pg_url,
        "embed_url": embed_url or os.environ.get("GATEWAYAIVECTORMEMORY_EMBED_URL", ""),
        "user_id": user_id,
        "token": token or "",
        "project_dir": project_dir or "",
    }

    if daemon:
        if not hasattr(os, "fork"):
            print("[gatewayaivectormemory-web] --daemon not supported on Windows", file=sys.stderr)
            sys.exit(1)
        pid = os.fork()
        if pid > 0:
            print(f"[gatewayaivectormemory-web] Running in background (PID {pid})", file=sys.stderr)
            sys.exit(0)
        os.setsid()
        sys.stdin.close()
        devnull = open(os.devnull, "w")
        sys.stdout = devnull
        sys.stderr = devnull

    import uvicorn
    app = create_app(config)
    log_level = "warning" if quiet else "info"
    print(f"[gatewayaivectormemory-web] Web dashboard: http://{bind}:{port}", file=sys.stderr)
    if token:
        print("[gatewayaivectormemory-web] Token auth enabled", file=sys.stderr)
    uvicorn.run(app, host=bind, port=port, log_level=log_level)
