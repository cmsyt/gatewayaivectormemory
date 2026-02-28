import json
import traceback

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from gatewayaivectormemory.db.connection import ConnectionManager
from gatewayaivectormemory.db.state_repo import StateRepo
from gatewayaivectormemory.tools import TOOL_HANDLERS
from gatewayaivectormemory.proxy.app import get_state

from gatewayaivectormemory.proxy.auth import AuthInfo


router = APIRouter(prefix="/memory")

TOOLS_REQUIRING_ENGINE = {"remember", "recall", "auto_save", "track"}
TOOLS_REQUIRING_SESSION = {"remember", "auto_save"}


def _extract_headers(request: Request) -> tuple[str, str]:
    """提取并验证请求头，根据角色决定 user_id 来源"""
    auth: AuthInfo = getattr(request.state, "auth", None) or AuthInfo()
    project_dir = request.headers.get("x-project-dir", "")
    if not project_dir:
        raise ValueError("X-Project-Dir header is required")

    if auth.role == "admin":
        # admin 可以使用 header 中的 user_id，也可以不传（查看所有）
        user_id = request.headers.get("x-user-id", "")
    else:
        # user 角色：强制使用认证中的 user_id，忽略 header
        user_id = auth.user_id or request.headers.get("x-user-id", "")

    if not user_id:
        raise ValueError("X-User-Id header is required")
    return user_id, project_dir


async def _call_tool(tool_name: str, request: Request) -> JSONResponse:
    try:
        user_id, project_dir = _extract_headers(request)
    except ValueError as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=400)

    handler = TOOL_HANDLERS.get(tool_name)
    if not handler:
        return JSONResponse({"success": False, "error": f"Unknown tool: {tool_name}"}, status_code=404)

    try:
        body = await request.json()
    except Exception:
        body = {}

    st = get_state()
    parent_cm: ConnectionManager = st["cm"]
    cm = ConnectionManager(parent_cm.pg_url, project_dir=project_dir, user_id=user_id)
    cm._pool = parent_cm._pool  # share connection pool

    kwargs = {"cm": cm}
    if tool_name in TOOLS_REQUIRING_ENGINE:
        kwargs["engine"] = st["engine"]
    if tool_name in TOOLS_REQUIRING_SESSION:
        repo = StateRepo(cm, project_dir, user_id)
        kwargs["session_id"] = repo.get_session_id()

    try:
        result = handler(body, **kwargs)
        data = json.loads(result) if isinstance(result, str) else result
        return JSONResponse({"success": True, "data": data})
    except Exception as e:
        traceback.print_exc()
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


@router.post("/remember")
async def remember(request: Request):
    return await _call_tool("remember", request)


@router.post("/recall")
async def recall(request: Request):
    return await _call_tool("recall", request)


@router.post("/forget")
async def forget(request: Request):
    return await _call_tool("forget", request)


@router.post("/status")
async def status(request: Request):
    return await _call_tool("status", request)


@router.post("/track")
async def track(request: Request):
    return await _call_tool("track", request)


@router.post("/task")
async def task(request: Request):
    return await _call_tool("task", request)


@router.post("/auto_save")
async def auto_save(request: Request):
    return await _call_tool("auto_save", request)
