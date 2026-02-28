import json
from gatewayaivectormemory.db.memory_repo import MemoryRepo
from gatewayaivectormemory.db.user_memory_repo import UserMemoryRepo
from gatewayaivectormemory.db.team_memory_repo import TeamMemoryRepo
from gatewayaivectormemory.errors import success_response


def handle_forget(args, *, cm, **_):
    mid = args.get("memory_id")
    mids = args.get("memory_ids", [])
    tags = args.get("tags")
    scope = args.get("scope", "all")

    mem_repo = MemoryRepo(cm, cm.project_dir, cm.user_id)
    user_repo = UserMemoryRepo(cm, cm.user_id)
    team_repo = TeamMemoryRepo(cm, cm.project_dir)

    if tags:
        ids = []
        if scope in ("project", "all"):
            ids += [r["id"] for r in mem_repo.list_by_tags(tags, scope="project", project_dir=cm.project_dir, limit=10000)]
        if scope in ("user", "all"):
            ids += [r["id"] for r in user_repo.list_by_tags(tags, limit=10000)]
        if scope in ("team", "all"):
            ids += [r["id"] for r in team_repo.list_by_tags(tags, limit=10000)]
    else:
        ids = [mid] if mid else mids

    if not ids:
        raise ValueError("memory_id, memory_ids, or tags is required")

    deleted = []
    not_found = []
    for i in ids:
        if scope == "user":
            ok = user_repo.delete(i)
        elif scope == "project":
            ok = mem_repo.delete(i)
        elif scope == "team":
            ok = team_repo.delete(i)
        else:
            ok = mem_repo.delete(i) or user_repo.delete(i) or team_repo.delete(i)
        (deleted if ok else not_found).append(i)

    return json.dumps(success_response(deleted_count=len(deleted), ids=deleted, not_found=not_found))
