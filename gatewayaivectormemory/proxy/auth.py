"""认证与鉴权模块：静态 token / user-tokens / JWT 三种模式"""
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

import jwt
from fastapi import Request
from fastapi.responses import JSONResponse


@dataclass
class AuthInfo:
    user_id: str = ""
    role: str = ""  # "admin" | "user" | ""
    authenticated: bool = False


@dataclass
class AuthConfig:
    token: str = ""
    jwt_secret: str = ""
    user_tokens: dict[str, str] = field(default_factory=dict)  # token -> user_id


def load_auth_config(config: dict) -> AuthConfig:
    """从 app config 加载认证配置，执行互斥校验"""
    token = config.get("token", "") or ""
    jwt_secret = config.get("jwt_secret", "") or ""
    user_tokens_path = config.get("user_tokens", "") or ""

    if token and jwt_secret:
        print("[memory-proxy] ERROR: --token and --jwt-secret are mutually exclusive", file=sys.stderr)
        sys.exit(1)

    user_tokens: dict[str, str] = {}
    if user_tokens_path:
        try:
            raw = Path(user_tokens_path).read_text(encoding="utf-8")
            user_tokens = json.loads(raw)
            if not isinstance(user_tokens, dict):
                print(f"[memory-proxy] ERROR: --user-tokens must be a JSON object (token -> user_id)", file=sys.stderr)
                sys.exit(1)
            print(f"[memory-proxy] Loaded {len(user_tokens)} user tokens", file=sys.stderr)
        except FileNotFoundError:
            print(f"[memory-proxy] ERROR: --user-tokens file not found: {user_tokens_path}", file=sys.stderr)
            sys.exit(1)
        except json.JSONDecodeError as e:
            print(f"[memory-proxy] ERROR: --user-tokens invalid JSON: {e}", file=sys.stderr)
            sys.exit(1)

    return AuthConfig(token=token, jwt_secret=jwt_secret, user_tokens=user_tokens)


def auth_enabled(auth_cfg: AuthConfig) -> bool:
    return bool(auth_cfg.token or auth_cfg.jwt_secret or auth_cfg.user_tokens)


def authenticate(request: Request, auth_cfg: AuthConfig) -> AuthInfo:
    """从请求中提取认证信息，返回 AuthInfo"""
    auth_header = request.headers.get("authorization", "")
    bearer_token = auth_header.removeprefix("Bearer ").strip() if auth_header.startswith("Bearer ") else ""

    if not bearer_token:
        return AuthInfo()

    # 1. 静态 admin token
    if auth_cfg.token and bearer_token == auth_cfg.token:
        return AuthInfo(user_id="", role="admin", authenticated=True)

    # 2. user-tokens 映射
    if auth_cfg.user_tokens and bearer_token in auth_cfg.user_tokens:
        uid = auth_cfg.user_tokens[bearer_token]
        return AuthInfo(user_id=uid, role="user", authenticated=True)

    # 3. JWT 认证
    if auth_cfg.jwt_secret:
        try:
            payload = jwt.decode(bearer_token, auth_cfg.jwt_secret, algorithms=["HS256"])
            uid = payload.get("user_id", "")
            role = payload.get("role", "user")
            return AuthInfo(user_id=uid, role=role, authenticated=True)
        except jwt.ExpiredSignatureError:
            return AuthInfo()
        except jwt.InvalidTokenError:
            return AuthInfo()

    return AuthInfo()


def check_localhost_only(request: Request) -> bool:
    """无认证时检查是否为本地访问"""
    host = request.client.host if request.client else ""
    return host in ("127.0.0.1", "::1", "localhost")


def check_bind_warning(bind: str, auth_cfg: AuthConfig):
    """bind 0.0.0.0 且无认证时输出警告"""
    if bind == "0.0.0.0" and not auth_enabled(auth_cfg):
        print(
            "[memory-proxy] WARNING: binding to 0.0.0.0 without authentication. "
            "Use --token, --jwt-secret, or --user-tokens for security.",
            file=sys.stderr,
        )
