import json
from gatewayaivectormemory.config import DEDUP_THRESHOLD
from gatewayaivectormemory.db.memory_repo import MemoryRepo
from gatewayaivectormemory.db.user_memory_repo import UserMemoryRepo
from gatewayaivectormemory.db.team_memory_repo import TeamMemoryRepo
from gatewayaivectormemory.errors import success_response
from gatewayaivectormemory.tools.keywords import extract_keywords


def handle_remember(args, *, cm, engine, session_id, **_):
    content = args.get("content")
    tags = args.get("tags", [])
    scope = args.get("scope", "project")

    if not content:
        raise ValueError("content is required")
    if not isinstance(tags, list):
        raise ValueError("tags must be a list")
    if scope not in ("user", "project", "team"):
        raise ValueError("scope must be one of: user, project, team")
    if len(content) > 5000:
        content = content[:5000]

    # 自动从 content 提取关键词补充到 tags
    existing = {t.lower() for t in tags}
    for kw in extract_keywords(content):
        if kw.lower() not in existing:
            tags.append(kw)
            existing.add(kw.lower())

    embedding = engine.encode(content)

    if scope == "user":
        repo = UserMemoryRepo(cm, cm.user_id)
        result = repo.insert(content, tags, session_id, embedding, DEDUP_THRESHOLD)
    elif scope == "team":
        repo = TeamMemoryRepo(cm, cm.project_dir)
        result = repo.insert(content, tags, cm.user_id, session_id, embedding, DEDUP_THRESHOLD)
    else:
        repo = MemoryRepo(cm, cm.project_dir, cm.user_id)
        result = repo.insert(content, tags, scope, session_id, embedding, DEDUP_THRESHOLD)

    return json.dumps(success_response(
        id=result["id"], action=result["action"],
        tags=tags, scope=scope
    ))
