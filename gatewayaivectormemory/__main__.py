import argparse
import io
import sys


def _ensure_utf8_stdio():
    """确保 stdin/stdout 使用 UTF-8 编码（Windows pipe 默认可能是 GBK/CP936）"""
    if sys.stdin.encoding.lower().replace("-", "") != "utf8":
        sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding="utf-8")
    if sys.stdout.encoding.lower().replace("-", "") != "utf8":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    if sys.stderr.encoding.lower().replace("-", "") != "utf8":
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")


def main():
    _ensure_utf8_stdio()
    parser = argparse.ArgumentParser(prog="team-run", description="GatewayAIVectorMemory MCP Server")
    parser.add_argument("--project-dir", default=None, help="项目根目录，默认当前目录")
    sub = parser.add_subparsers(dest="command")

    web_parser = sub.add_parser("web", help="启动 Web 看板")
    web_parser.add_argument("--port", type=int, default=9080, help="Web 看板端口")
    web_parser.add_argument("--bind", default="127.0.0.1", help="绑定地址，默认 127.0.0.1")
    web_parser.add_argument("--token", default=None, help="API 认证 token，启用后所有 API 请求需带 ?token=xxx")
    web_parser.add_argument("--pg-url", default=None, help="PostgreSQL 连接 URL")
    web_parser.add_argument("--embed-url", default=None, help="Embed Server URL")
    web_parser.add_argument("--user-id", default=None, help="用户 ID（不传时展示全部 = 管理员模式）")
    web_parser.add_argument("--quiet", action="store_true", default=False, help="屏蔽请求日志")
    web_parser.add_argument("--daemon", action="store_true", default=False, help="后台运行（macOS/Linux）")
    web_parser.add_argument("--project-dir", dest="web_project_dir", default=None)

    embed_parser = sub.add_parser("embed-server", help="启动 Embedding 共享服务")
    embed_parser.add_argument("--port", type=int, default=8900, help="服务端口")
    embed_parser.add_argument("--bind", default="127.0.0.1", help="绑定地址")
    embed_parser.add_argument("--daemon", action="store_true", default=False, help="后台运行")

    proxy_parser = sub.add_parser("memory-proxy", help="启动 Memory Proxy HTTP 服务")
    proxy_parser.add_argument("--port", type=int, default=8080, help="服务端口")
    proxy_parser.add_argument("--bind", default="0.0.0.0", help="绑定地址")
    proxy_parser.add_argument("--pg-url", default=None, help="PostgreSQL 连接 URL")
    proxy_parser.add_argument("--embed-url", default=None, help="Embed Server URL")
    proxy_parser.add_argument("--token", default=None, help="API 认证 token")
    proxy_parser.add_argument("--jwt-secret", default=None, help="JWT 签名密钥")
    proxy_parser.add_argument("--user-tokens", default=None, help="用户 token 映射 JSON 文件路径")
    proxy_parser.add_argument("--workers", type=int, default=4, help="Worker 数量")

    args = parser.parse_args()

    if args.command == "web":
        project_dir = args.web_project_dir or args.project_dir
        from gatewayaivectormemory.web.app import run_web
        run_web(pg_url=args.pg_url or "", port=args.port, bind=args.bind,
                token=args.token, quiet=args.quiet, daemon=args.daemon,
                user_id=args.user_id or "", embed_url=args.embed_url or "",
                project_dir=project_dir)
    elif args.command == "embed-server":
        from gatewayaivectormemory.embedding.server import run_embed_server
        run_embed_server(port=args.port, bind=args.bind, daemon=args.daemon)
    elif args.command == "memory-proxy":
        import os, uvicorn
        pg_url = args.pg_url or os.environ.get("GATEWAYAIVECTORMEMORY_PG_URL", "")
        embed_url = args.embed_url or os.environ.get("GATEWAYAIVECTORMEMORY_EMBED_URL", "")
        if not pg_url:
            print("Error: --pg-url or GATEWAYAIVECTORMEMORY_PG_URL is required", file=sys.stderr)
            sys.exit(1)
        os.environ["GATEWAYAIVECTORMEMORY_PG_URL"] = pg_url
        if embed_url:
            os.environ["GATEWAYAIVECTORMEMORY_EMBED_URL"] = embed_url
            os.environ["EMBEDDING_SERVER_URL"] = embed_url
        if args.token:
            os.environ["GATEWAYAIVECTORMEMORY_TOKEN"] = args.token
        if args.jwt_secret:
            os.environ["GATEWAYAIVECTORMEMORY_JWT_SECRET"] = args.jwt_secret
        if args.user_tokens:
            os.environ["GATEWAYAIVECTORMEMORY_USER_TOKENS"] = args.user_tokens
        if args.workers > 1:
            from gatewayaivectormemory.proxy.auth import load_auth_config, check_bind_warning
            _cfg = {"token": args.token or "", "jwt_secret": args.jwt_secret or "", "user_tokens": args.user_tokens or ""}
            check_bind_warning(args.bind, load_auth_config(_cfg))
            uvicorn.run(
                "gatewayaivectormemory.proxy.app:create_app",
                factory=True,
                host=args.bind, port=args.port,
                workers=args.workers, log_level="info",
            )
        else:
            from gatewayaivectormemory.proxy.app import create_app
            from gatewayaivectormemory.proxy.auth import load_auth_config, check_bind_warning
            _cfg = {"token": args.token or "", "jwt_secret": args.jwt_secret or "", "user_tokens": args.user_tokens or ""}
            check_bind_warning(args.bind, load_auth_config(_cfg))
            app = create_app()
            uvicorn.run(app, host=args.bind, port=args.port, log_level="info")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
