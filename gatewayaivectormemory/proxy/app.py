import sys
import json
import time
import urllib.request
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from gatewayaivectormemory.db.connection import ConnectionManager
from gatewayaivectormemory.db.schema import init_db
from gatewayaivectormemory.embedding.engine import EmbeddingEngine
from gatewayaivectormemory.proxy.auth import (
    AuthConfig, AuthInfo, load_auth_config, auth_enabled,
    authenticate, check_localhost_only,
)
from gatewayaivectormemory.tools import TOOL_HANDLERS


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
    print(f"[memory-proxy] PostgreSQL connected", file=sys.stderr)

    engine = EmbeddingEngine()
    engine.load()
    print(f"[memory-proxy] EmbeddingEngine ready (remote={engine.is_remote})", file=sys.stderr)

    embed_ok = _check_embed(cfg.get("embed_url", ""))
    if embed_ok:
        print(f"[memory-proxy] Embed server reachable: {cfg['embed_url']}", file=sys.stderr)
    else:
        print(f"[memory-proxy] Embed server not reachable (using engine fallback)", file=sys.stderr)

    _state["cm"] = cm
    _state["engine"] = engine
    _state["embed_ok"] = embed_ok

    auth_cfg = load_auth_config(cfg)
    _state["auth_cfg"] = auth_cfg
    if auth_enabled(auth_cfg):
        mode = "token" if auth_cfg.token else ("jwt" if auth_cfg.jwt_secret else "user-tokens")
        print(f"[memory-proxy] Auth enabled: {mode}", file=sys.stderr)
    else:
        print("[memory-proxy] Auth disabled (localhost only)", file=sys.stderr)

    yield
    cm.close()


def _check_embed(embed_url: str) -> bool:
    if not embed_url:
        return False
    try:
        req = urllib.request.Request(f"{embed_url.rstrip('/')}/health")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
            return data.get("status") == "ok"
    except Exception:
        return False


def create_app(config: dict | None = None) -> FastAPI:
    if config is None:
        import os
        config = {
            "pg_url": os.environ.get("GATEWAYAIVECTORMEMORY_PG_URL", ""),
            "embed_url": os.environ.get("GATEWAYAIVECTORMEMORY_EMBED_URL", ""),
            "token": os.environ.get("GATEWAYAIVECTORMEMORY_TOKEN", ""),
            "jwt_secret": os.environ.get("GATEWAYAIVECTORMEMORY_JWT_SECRET", ""),
            "user_tokens": os.environ.get("GATEWAYAIVECTORMEMORY_USER_TOKENS", ""),
        }
    app = FastAPI(title="Memory Proxy", lifespan=lifespan)
    app.state.config = config

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def auth_middleware(request: Request, call_next):
        # health 端点不需要认证
        if request.url.path == "/memory/health":
            return await call_next(request)

        auth_cfg: AuthConfig = get_state().get("auth_cfg")
        if auth_cfg and auth_enabled(auth_cfg):
            info = authenticate(request, auth_cfg)
            if not info.authenticated:
                return JSONResponse({"detail": "Unauthorized"}, status_code=401)
            request.state.auth = info
        else:
            # 无认证时仅允许 localhost
            if not check_localhost_only(request):
                return JSONResponse({"detail": "Unauthorized: localhost only"}, status_code=401)
            request.state.auth = AuthInfo(role="admin", authenticated=True)

        return await call_next(request)

    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        start = time.time()
        response: Response = await call_next(request)
        latency = (time.time() - start) * 1000
        user_id = request.headers.get("x-user-id", "-")
        project_dir = request.headers.get("x-project-dir", "-")
        print(
            f"[memory-proxy] {request.method} {request.url.path} "
            f"user={user_id} project={project_dir} "
            f"status={response.status_code} {latency:.0f}ms",
            file=sys.stderr,
        )
        return response

    from gatewayaivectormemory.proxy.routes import router
    app.include_router(router)

    @app.get("/memory/health")
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
        embed_ok = st.get("embed_ok", False)
        return {
            "status": "ok" if pg_ok else "degraded",
            "postgresql": pg_ok,
            "embed_server": embed_ok,
        }

    return app
