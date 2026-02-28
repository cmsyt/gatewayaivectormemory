import json
from gatewayaivectormemory.config import DEFAULT_TOP_K
from gatewayaivectormemory.db.memory_repo import MemoryRepo
from gatewayaivectormemory.db.user_memory_repo import UserMemoryRepo
from gatewayaivectormemory.db.team_memory_repo import TeamMemoryRepo
from gatewayaivectormemory.db.issue_repo import IssueRepo
from gatewayaivectormemory.errors import success_response


BRIEF_KEYS = {"content", "tags"}


def _to_brief(rows):
    return [{k: r[k] for k in BRIEF_KEYS if k in r} for r in rows]


def _add_similarity(rows, has_tags=False):
    results = []
    for r in rows:
        distance = r.pop("distance", 0)
        r["similarity"] = round(1 - distance, 4) if has_tags else round(1 - (distance ** 2) / 2, 4)
        results.append(r)
    results.sort(key=lambda x: x["similarity"], reverse=True)
    return results


def handle_recall(args, *, cm, engine, **_):
    source = args.get("source")

    if source == "experience":
        return _recall_experience(args, cm=cm, engine=engine)

    scope = args.get("scope", "all")
    query = args.get("query")
    tags = args.get("tags")
    top_k = args.get("top_k", DEFAULT_TOP_K)
    brief = args.get("brief", False)

    if scope == "user":
        rows = _query_user(cm, engine, query, tags, top_k, source)
    elif scope == "project":
        rows = _query_project(cm, engine, query, tags, top_k, source)
    elif scope == "team":
        rows = _query_team(cm, engine, query, tags, top_k)
    else:
        rows = _query_all(cm, engine, query, tags, top_k, source)

    return json.dumps(success_response(memories=_to_brief(rows) if brief else rows))


def _query_user(cm, engine, query, tags, top_k, source):
    repo = UserMemoryRepo(cm, cm.user_id)
    if not query:
        if not tags:
            raise ValueError("query or tags is required")
        rows = repo.list_by_tags(tags, limit=top_k, source=source)
        for r in rows:
            r["similarity"] = 1.0
        return rows
    embedding = engine.encode(query)
    if tags:
        return _add_similarity(repo.search_by_vector_with_tags(embedding, tags, top_k=top_k), has_tags=True)
    return _add_similarity(repo.search_by_vector(embedding, top_k=top_k))


def _query_project(cm, engine, query, tags, top_k, source):
    repo = MemoryRepo(cm, cm.project_dir, cm.user_id)
    if not query:
        if not tags:
            raise ValueError("query or tags is required")
        rows = repo.list_by_tags(tags, scope="project", project_dir=cm.project_dir, limit=top_k, source=source)
        for r in rows:
            r["similarity"] = 1.0
        return rows
    embedding = engine.encode(query)
    if tags:
        return _add_similarity(repo.search_by_vector_with_tags(embedding, tags, top_k=top_k, scope="project", project_dir=cm.project_dir, source=source), has_tags=True)
    return _add_similarity(repo.search_by_vector(embedding, top_k=top_k, scope="project", project_dir=cm.project_dir, source=source))


def _query_all(cm, engine, query, tags, top_k, source):
    proj = _query_project(cm, engine, query, tags, top_k, source)
    user = _query_user(cm, engine, query, tags, top_k, source)
    team = _query_team(cm, engine, query, tags, top_k)
    merged = proj + user + team
    merged.sort(key=lambda x: x.get("similarity", 0), reverse=True)
    return merged[:top_k]


def _query_team(cm, engine, query, tags, top_k):
    repo = TeamMemoryRepo(cm, cm.project_dir)
    if not query:
        if not tags:
            raise ValueError("query or tags is required")
        rows = repo.list_by_tags(tags, limit=top_k)
        for r in rows:
            r["similarity"] = 1.0
            r["scope"] = "team"
        return rows
    embedding = engine.encode(query)
    if tags:
        rows = _add_similarity(repo.search_by_vector_with_tags(embedding, tags, top_k=top_k), has_tags=True)
    else:
        rows = _add_similarity(repo.search_by_vector(embedding, top_k=top_k))
    for r in rows:
        r["scope"] = "team"
    return rows


def _recall_experience(args, *, cm, engine):
    query = args.get("query")
    if not query:
        raise ValueError("query is required for source=experience")
    top_k = args.get("top_k", DEFAULT_TOP_K)
    brief = args.get("brief", False)

    embedding = engine.encode(query)
    issue_repo = IssueRepo(cm, cm.project_dir, cm.user_id, engine=engine)
    rows = issue_repo.search_archive_by_vector(embedding, top_k=top_k)

    results = []
    for r in rows:
        content = f"{r['title']}\n根因：{r['root_cause'] or ''}\n方案：{r['solution'] or ''}"
        results.append({
            "id": r["id"],
            "content": content,
            "tags": ["经验"],
            "similarity": r["similarity"],
        })
    return json.dumps(success_response(memories=_to_brief(results) if brief else results))
