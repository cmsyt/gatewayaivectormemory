import json
import os
from datetime import date, datetime

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from gatewayaivectormemory.db.connection import ConnectionManager
from gatewayaivectormemory.db.memory_repo import MemoryRepo
from gatewayaivectormemory.db.user_memory_repo import UserMemoryRepo
from gatewayaivectormemory.db.team_memory_repo import TeamMemoryRepo
from gatewayaivectormemory.db.state_repo import StateRepo
from gatewayaivectormemory.db.issue_repo import IssueRepo
from gatewayaivectormemory.db.task_repo import TaskRepo


def _get_cm(request: Request) -> ConnectionManager:
    """获取共享 ConnectionManager"""
    from gatewayaivectormemory.web.app import get_state
    return get_state()["cm"]


def _get_engine(request: Request):
    from gatewayaivectormemory.web.app import get_state
    return get_state().get("engine")


def _get_config(request: Request) -> dict:
    from gatewayaivectormemory.web.app import get_state
    return get_state().get("config", {})


def _user_id(request: Request) -> str:
    cfg = _get_config(request)
    return cfg.get("user_id", "")


def _project_dir(request: Request, params: dict = None) -> str:
    """从 query param 或 config 获取 project_dir"""
    if params and params.get("project"):
        return params["project"]
    cfg = _get_config(request)
    return cfg.get("project_dir", "")


def _make_cm(request: Request, pdir: str = "") -> ConnectionManager:
    """创建 per-request ConnectionManager，共享连接池"""
    parent_cm = _get_cm(request)
    uid = _user_id(request)
    pd = pdir or _project_dir(request)
    cm = ConnectionManager(parent_cm.pg_url, project_dir=pd, user_id=uid)
    cm._pool = parent_cm._pool
    return cm


def register_routes(app: FastAPI):

    # ── Memories ──

    @app.get("/api/memories")
    async def api_get_memories(request: Request):
        params = dict(request.query_params)
        pdir = _project_dir(request, params)
        cm = _make_cm(request, pdir)
        scope = params.get("scope", "all")
        query = params.get("query")
        tag = params.get("tag")
        source = params.get("source")
        exclude_tags = params.get("exclude_tags")
        limit = int(params.get("limit", 100))
        offset = int(params.get("offset", 0))

        repo = MemoryRepo(cm, pdir, cm.user_id)
        user_repo = UserMemoryRepo(cm, cm.user_id)
        team_repo = TeamMemoryRepo(cm, pdir)

        if tag:
            if scope == "user":
                all_rows = user_repo.list_by_tags([tag], limit=9999, source=source)
            elif scope == "team":
                all_rows = team_repo.list_by_tags([tag], limit=9999)
            elif scope == "project":
                all_rows = repo.list_by_tags([tag], scope="project", project_dir=pdir, limit=9999, source=source)
            else:
                proj_rows = repo.list_by_tags([tag], scope="project", project_dir=pdir, limit=9999, source=source)
                user_rows = user_repo.list_by_tags([tag], limit=9999, source=source)
                team_rows = team_repo.list_by_tags([tag], limit=9999)
                all_rows = proj_rows + user_rows + team_rows
            if query:
                q = query.lower()
                all_rows = [r for r in all_rows if q in r.get("content", "").lower()]
            total = len(all_rows)
            results = all_rows[offset:offset + limit]
        elif exclude_tags:
            ex_set = set(exclude_tags.split(","))
            if scope == "user":
                all_rows = user_repo.get_all(limit=9999)
            elif scope == "team":
                all_rows = team_repo.get_all(limit=9999)
            elif scope == "project":
                all_rows = repo.get_all(limit=9999, offset=0, project_dir=pdir)
            else:
                all_rows = repo.get_all(limit=9999, offset=0) + user_repo.get_all(limit=9999) + team_repo.get_all(limit=9999)
            all_rows = [r for r in all_rows if not ex_set.intersection(
                json.loads(r["tags"]) if isinstance(r["tags"], str) else (r["tags"] or []))]
            if source:
                all_rows = [r for r in all_rows if r.get("source", "manual") == source]
            if query:
                q = query.lower()
                all_rows = [r for r in all_rows if q in r.get("content", "").lower()]
            total = len(all_rows)
            results = all_rows[offset:offset + limit]
        else:
            if query:
                if scope == "user":
                    all_rows = user_repo.get_all(limit=9999)
                elif scope == "team":
                    all_rows = team_repo.get_all(limit=9999)
                elif scope == "project":
                    all_rows = repo.get_all(limit=9999, offset=0, project_dir=pdir)
                else:
                    all_rows = repo.get_all(limit=9999, offset=0) + user_repo.get_all(limit=9999) + team_repo.get_all(limit=9999)
                if source:
                    all_rows = [r for r in all_rows if r.get("source", "manual") == source]
                q = query.lower()
                all_rows = [r for r in all_rows if q in r.get("content", "").lower()]
                total = len(all_rows)
                results = all_rows[offset:offset + limit]
            else:
                if scope == "user":
                    rows = user_repo.get_all(limit=limit, offset=offset)
                    total = user_repo.count()
                elif scope == "team":
                    rows = team_repo.get_all(limit=limit, offset=offset)
                    total = team_repo.count()
                elif scope == "project":
                    rows = repo.get_all(limit=limit, offset=offset, project_dir=pdir)
                    total = repo.count(project_dir=pdir)
                else:
                    rows = repo.get_all(limit=limit, offset=offset)
                    total = repo.count() + user_repo.count() + team_repo.count()
                    if len(rows) < limit:
                        user_rows = user_repo.get_all(limit=limit - len(rows))
                        rows = rows + user_rows
                    if len(rows) < limit:
                        team_rows = team_repo.get_all(limit=limit - len(rows))
                        rows = rows + team_rows
                if source:
                    rows = [r for r in rows if r.get("source", "manual") == source]
                results = rows

        for r in results:
            if "created_by" in r:
                r["_scope"] = "team"
            elif r.get("scope") == "user" or (not r.get("project_dir") and not r.get("scope")):
                r["_scope"] = "user"
            else:
                r["_scope"] = "project"

        return {"memories": results, "total": total}

    @app.get("/api/memories/{mid}")
    async def api_get_memory_detail(mid: str, request: Request):
        params = dict(request.query_params)
        pdir = _project_dir(request, params)
        cm = _make_cm(request, pdir)
        repo = MemoryRepo(cm, pdir, cm.user_id)
        mem = repo.get_by_id(mid)
        if mem:
            return mem
        user_repo = UserMemoryRepo(cm, cm.user_id)
        mem = user_repo.get_by_id(mid)
        if mem:
            return mem
        with cm.get_conn() as conn:
            row = conn.execute("SELECT * FROM team_memories WHERE id=%s", (mid,)).fetchone()
        if row:
            from gatewayaivectormemory.db.memory_repo import _serialize_row
            return _serialize_row(dict(row))
        return {"error": "not found"}

    @app.put("/api/memories/{mid}")
    async def api_put_memory(mid: str, request: Request):
        body = await _read_body(request)
        params = dict(request.query_params)
        pdir = _project_dir(request, params)
        cm = _make_cm(request, pdir)
        repo = MemoryRepo(cm, pdir, cm.user_id)
        mem = repo.get_by_id(mid)
        table = "memories"
        if not mem:
            user_repo = UserMemoryRepo(cm, cm.user_id)
            mem = user_repo.get_by_id(mid)
            table = "user_memories"
        if not mem:
            with cm.get_conn() as conn:
                row = conn.execute("SELECT * FROM team_memories WHERE id=%s", (mid,)).fetchone()
            if row:
                table = "team_memories"
                mem = dict(row)
        if not mem:
            return {"error": "not found"}
        now = repo._now()
        updates = {}
        if "content" in body:
            updates["content"] = body["content"]
        if "tags" in body:
            updates["tags"] = json.dumps(body["tags"])
        if updates:
            updates["updated_at"] = now
            set_clause = ",".join(f"{k}=%s" for k in updates)
            with cm.get_conn() as conn:
                conn.execute(f"UPDATE {table} SET {set_clause} WHERE id=%s", [*updates.values(), mid])
        if table == "user_memories":
            return UserMemoryRepo(cm, cm.user_id).get_by_id(mid)
        if table == "team_memories":
            with cm.get_conn() as conn:
                row = conn.execute("SELECT * FROM team_memories WHERE id=%s", (mid,)).fetchone()
            from gatewayaivectormemory.db.memory_repo import _serialize_row
            return _serialize_row(dict(row)) if row else {"error": "not found"}
        return repo.get_by_id(mid)

    @app.delete("/api/memories/{mid}")
    async def api_delete_memory(mid: str, request: Request):
        params = dict(request.query_params)
        pdir = _project_dir(request, params)
        cm = _make_cm(request, pdir)
        repo = MemoryRepo(cm, pdir, cm.user_id)
        if repo.delete(mid):
            return {"deleted": True, "id": mid}
        user_repo = UserMemoryRepo(cm, cm.user_id)
        if user_repo.delete(mid):
            return {"deleted": True, "id": mid}
        team_repo = TeamMemoryRepo(cm, pdir)
        if team_repo.delete(mid):
            return {"deleted": True, "id": mid}
        return {"error": "not found"}

    @app.delete("/api/memories")
    async def api_delete_memories_batch(request: Request):
        body = await _read_body(request)
        ids = body.get("ids", [])
        params = dict(request.query_params)
        pdir = _project_dir(request, params)
        cm = _make_cm(request, pdir)
        repo = MemoryRepo(cm, pdir, cm.user_id)
        user_repo = UserMemoryRepo(cm, cm.user_id)
        team_repo = TeamMemoryRepo(cm, pdir)
        deleted = []
        for mid in ids:
            if repo.delete(mid):
                deleted.append(mid)
            elif user_repo.delete(mid):
                deleted.append(mid)
            elif team_repo.delete(mid):
                deleted.append(mid)
        return {"deleted_count": len(deleted), "ids": deleted}

    # ── Status ──

    @app.get("/api/status")
    async def api_get_status(request: Request):
        params = dict(request.query_params)
        pdir = _project_dir(request, params)
        cm = _make_cm(request, pdir)
        repo = StateRepo(cm, pdir, cm.user_id)
        state = repo.get()
        return state or {"empty": True}

    @app.put("/api/status")
    async def api_put_status(request: Request):
        body = await _read_body(request)
        params = dict(request.query_params)
        pdir = _project_dir(request, params)
        cm = _make_cm(request, pdir)
        repo = StateRepo(cm, pdir, cm.user_id)
        return repo.upsert(**body)

    # ── Issues ──

    @app.get("/api/issues")
    async def api_get_issues(request: Request):
        params = dict(request.query_params)
        pdir = _project_dir(request, params)
        cm = _make_cm(request, pdir)
        d = params.get("date")
        status = params.get("status")
        keyword = params.get("keyword")
        limit = int(params.get("limit", 20))
        offset = int(params.get("offset", 0))
        repo = IssueRepo(cm, pdir, cm.user_id)
        if status == "archived":
            issues, total = repo.list_archived(date=d, limit=limit, offset=offset, keyword=keyword)
        elif status == "all":
            issues, total = repo.list_all(date=d, limit=limit, offset=offset, keyword=keyword)
        elif status:
            issues, total = repo.list_by_date(date=d, status=status, limit=limit, offset=offset, keyword=keyword)
        else:
            issues, total = repo.list_by_date(date=d, limit=limit, offset=offset, keyword=keyword)
        task_repo = TaskRepo(cm, pdir, cm.user_id)
        for issue in issues:
            fid = issue.get("feature_id", "")
            if fid:
                all_tasks = task_repo.list_by_feature(feature_id=fid)
                total_t, done_t = 0, 0
                for t in all_tasks:
                    kids = t.get("children", [])
                    if kids:
                        total_t += len(kids)
                        done_t += sum(1 for k in kids if k["status"] == "completed")
                    else:
                        total_t += 1
                        if t["status"] == "completed":
                            done_t += 1
                issue["task_progress"] = {"total": total_t, "done": done_t}
        return {"issues": issues, "total": total}

    @app.get("/api/issues/{inum:int}")
    async def api_get_issue(inum: int, request: Request):
        params = dict(request.query_params)
        pdir = _project_dir(request, params)
        cm = _make_cm(request, pdir)
        repo = IssueRepo(cm, pdir, cm.user_id)
        row = repo.get_by_number(inum)
        if not row:
            row = repo.get_archived_by_number(inum)
        return dict(row) if row else {"error": "not found"}

    @app.put("/api/issues/{inum:int}")
    async def api_put_issue(inum: int, request: Request):
        body = await _read_body(request)
        params = dict(request.query_params)
        pdir = _project_dir(request, params)
        cm = _make_cm(request, pdir)
        repo = IssueRepo(cm, pdir, cm.user_id)
        row = repo.get_by_number(inum)
        if not row:
            return {"error": "not found"}
        iid = row["id"]
        fields = {k: body[k] for k in ("title", "status", "content",
                  "description", "investigation", "root_cause", "solution",
                  "files_changed", "test_result", "notes", "feature_id") if k in body}
        result = repo.update(iid, **fields)
        return result or {"error": "not found"}

    @app.post("/api/issues")
    async def api_post_issue(request: Request):
        body = await _read_body(request)
        title = body.get("title", "").strip()
        if not title:
            return {"error": "title required"}
        content = body.get("content", "")
        params = dict(request.query_params)
        pdir = _project_dir(request, params)
        cm = _make_cm(request, pdir)
        repo = IssueRepo(cm, pdir, cm.user_id)
        parent_id = body.get("parent_id", 0)
        d = body.get("date", date.today().isoformat())
        result = repo.create(d, title, content, parent_id=parent_id)
        return result

    @app.delete("/api/issues/{inum:int}")
    async def api_delete_issue(inum: int, request: Request):
        params = dict(request.query_params)
        action = params.get("action", "delete")
        pdir = _project_dir(request, params)
        cm = _make_cm(request, pdir)
        repo = IssueRepo(cm, pdir, cm.user_id)
        row = repo.get_by_number(inum)
        is_archived = row is None
        if is_archived:
            row = repo.get_archived_by_number(inum)
        if not row:
            return {"error": "not found"}
        iid = row["id"]
        if action == "archive":
            result = repo.archive(iid)
            return result or {"error": "not found"}
        if is_archived:
            result = repo.delete_archived(iid)
        else:
            result = repo.delete(iid)
        if not result:
            return {"error": "not found"}
        memory_id = result.get("memory_id", "")
        if memory_id:
            MemoryRepo(cm, pdir, cm.user_id).delete(memory_id)
        return result

    # ── Tasks ──

    @app.get("/api/tasks")
    async def api_get_tasks(request: Request):
        params = dict(request.query_params)
        pdir = _project_dir(request, params)
        cm = _make_cm(request, pdir)
        repo = TaskRepo(cm, pdir, cm.user_id)
        feature_id = params.get("feature_id")
        status = params.get("status")
        tasks = repo.list_by_feature(feature_id=feature_id, status=status)
        return {"tasks": tasks}

    @app.get("/api/tasks/archived")
    async def api_get_archived_tasks(request: Request):
        params = dict(request.query_params)
        pdir = _project_dir(request, params)
        cm = _make_cm(request, pdir)
        repo = TaskRepo(cm, pdir, cm.user_id)
        feature_id = params.get("feature_id")
        tasks = repo.list_archived(feature_id=feature_id)
        return {"tasks": tasks}

    @app.post("/api/tasks")
    async def api_post_tasks(request: Request):
        body = await _read_body(request)
        params = dict(request.query_params)
        pdir = _project_dir(request, params)
        cm = _make_cm(request, pdir)
        repo = TaskRepo(cm, pdir, cm.user_id)
        feature_id = body.get("feature_id", "").strip()
        if not feature_id:
            return {"error": "feature_id is required"}
        tasks = body.get("tasks", [])
        if not tasks:
            return {"error": "tasks array is required"}
        result = repo.batch_create(feature_id, tasks, task_type=body.get("task_type", "manual"))
        return result

    @app.put("/api/tasks/{tid:int}")
    async def api_put_task(tid: int, request: Request):
        body = await _read_body(request)
        params = dict(request.query_params)
        pdir = _project_dir(request, params)
        cm = _make_cm(request, pdir)
        repo = TaskRepo(cm, pdir, cm.user_id)
        fields = {k: body[k] for k in ("status", "title") if k in body}
        result = repo.update(tid, **fields)
        return {"task": result} if result else {"error": "not found"}

    @app.delete("/api/tasks/{tid:int}")
    async def api_delete_task(tid: int, request: Request):
        params = dict(request.query_params)
        pdir = _project_dir(request, params)
        cm = _make_cm(request, pdir)
        repo = TaskRepo(cm, pdir, cm.user_id)
        result = repo.delete(tid)
        return result if result else {"error": "not found"}

    @app.delete("/api/tasks")
    async def api_delete_tasks_by_feature(request: Request):
        params = dict(request.query_params)
        feature_id = params.get("feature_id")
        if not feature_id:
            return {"error": "feature_id is required"}
        pdir = _project_dir(request, params)
        cm = _make_cm(request, pdir)
        repo = TaskRepo(cm, pdir, cm.user_id)
        count = repo.delete_by_feature(feature_id)
        return {"deleted": count, "feature_id": feature_id}

    # ── Stats ──

    @app.get("/api/stats")
    async def api_get_stats(request: Request):
        params = dict(request.query_params)
        pdir = _project_dir(request, params)
        cm = _make_cm(request, pdir)
        repo = MemoryRepo(cm, pdir, cm.user_id)
        user_repo = UserMemoryRepo(cm, cm.user_id)
        team_repo = TeamMemoryRepo(cm, pdir)
        issue_repo = IssueRepo(cm, pdir, cm.user_id)

        proj_count = repo.count(project_dir=pdir)
        user_count = user_repo.count()
        team_count = team_repo.count()
        total_count = repo.count() + user_count + team_count

        all_issues, _ = issue_repo.list_by_date()
        status_counts = {}
        for i in all_issues:
            s = i["status"]
            status_counts[s] = status_counts.get(s, 0) + 1
        _, archived_total = issue_repo.list_archived()
        status_counts["archived"] = archived_total

        tag_counts = _merged_tag_counts(repo, user_repo, team_repo, pdir)

        return {
            "memories": {"project": proj_count, "user": user_count, "team": team_count, "total": total_count},
            "issues": status_counts,
            "tags": tag_counts,
        }

    # ── Tags ──

    @app.get("/api/tags")
    async def api_get_tags(request: Request):
        params = dict(request.query_params)
        query = params.get("query")
        pdir = _project_dir(request, params)
        cm = _make_cm(request, pdir)
        repo = MemoryRepo(cm, pdir, cm.user_id)
        user_repo = UserMemoryRepo(cm, cm.user_id)
        team_repo = TeamMemoryRepo(cm, pdir)
        proj = repo.get_tag_counts(project_dir=pdir)
        user = user_repo.get_tag_counts()
        team = _team_tag_counts(cm, pdir)
        all_names = sorted(set(proj) | set(user) | set(team),
                           key=lambda k: -(proj.get(k, 0) + user.get(k, 0) + team.get(k, 0)))
        tags = [{"name": k, "count": proj.get(k, 0) + user.get(k, 0) + team.get(k, 0),
                 "project_count": proj.get(k, 0), "user_count": user.get(k, 0),
                 "team_count": team.get(k, 0)} for k in all_names]
        if query:
            q = query.lower()
            tags = [t for t in tags if q in t["name"].lower()]
        return {"tags": tags, "total": len(tags)}

    @app.put("/api/tags/rename")
    async def api_rename_tag(request: Request):
        body = await _read_body(request)
        old_name = body.get("old_name", "")
        new_name = body.get("new_name", "").strip()
        if not old_name or not new_name:
            return {"error": "old_name and new_name required"}
        params = dict(request.query_params)
        pdir = _project_dir(request, params)
        cm = _make_cm(request, pdir)
        repo = MemoryRepo(cm, pdir, cm.user_id)
        user_repo = UserMemoryRepo(cm, cm.user_id)
        updated = 0
        for m in _merged_ids_with_tag(repo, user_repo, old_name, pdir):
            tags = json.loads(m["tags"]) if isinstance(m.get("tags"), str) else m.get("tags", [])
            tags = [new_name if t == old_name else t for t in tags]
            tags = list(dict.fromkeys(tags))
            table = "user_memories" if user_repo.get_by_id(m["id"]) else "memories"
            with cm.get_conn() as conn:
                conn.execute(f"UPDATE {table} SET tags=%s, updated_at=%s WHERE id=%s",
                             (json.dumps(tags, ensure_ascii=False), repo._now(), m["id"]))
            updated += 1
        # team_memories
        with cm.get_conn() as conn:
            rows = conn.execute("SELECT id, tags FROM team_memories WHERE project_dir=%s AND tags LIKE %s",
                                (pdir, f'%"{old_name}"%')).fetchall()
        for r in rows:
            tags = json.loads(r["tags"]) if isinstance(r["tags"], str) else (r["tags"] or [])
            tags = [new_name if t == old_name else t for t in tags]
            tags = list(dict.fromkeys(tags))
            with cm.get_conn() as conn:
                conn.execute("UPDATE team_memories SET tags=%s, updated_at=%s WHERE id=%s",
                             (json.dumps(tags, ensure_ascii=False), repo._now(), r["id"]))
            updated += 1
        return {"updated": updated, "old_name": old_name, "new_name": new_name}

    @app.put("/api/tags/merge")
    async def api_merge_tags(request: Request):
        body = await _read_body(request)
        source_tags = body.get("source_tags", [])
        target_name = body.get("target_name", "").strip()
        if not source_tags or not target_name:
            return {"error": "source_tags and target_name required"}
        params = dict(request.query_params)
        pdir = _project_dir(request, params)
        cm = _make_cm(request, pdir)
        repo = MemoryRepo(cm, pdir, cm.user_id)
        user_repo = UserMemoryRepo(cm, cm.user_id)
        updated = 0
        seen = set()
        for src in source_tags:
            for m in _merged_ids_with_tag(repo, user_repo, src, pdir):
                if m["id"] in seen:
                    continue
                seen.add(m["id"])
                tags = json.loads(m["tags"]) if isinstance(m.get("tags"), str) else m.get("tags", [])
                tags = [target_name if t in source_tags else t for t in tags]
                tags = list(dict.fromkeys(tags))
                table = "user_memories" if user_repo.get_by_id(m["id"]) else "memories"
                with cm.get_conn() as conn:
                    conn.execute(f"UPDATE {table} SET tags=%s, updated_at=%s WHERE id=%s",
                                 (json.dumps(tags, ensure_ascii=False), repo._now(), m["id"]))
                updated += 1
        return {"updated": updated, "target_name": target_name}

    @app.delete("/api/tags/delete")
    async def api_delete_tags(request: Request):
        body = await _read_body(request)
        tag_names = body.get("tags", [])
        if not tag_names:
            return {"error": "tags required"}
        params = dict(request.query_params)
        pdir = _project_dir(request, params)
        cm = _make_cm(request, pdir)
        repo = MemoryRepo(cm, pdir, cm.user_id)
        user_repo = UserMemoryRepo(cm, cm.user_id)
        updated = 0
        seen = set()
        for tn in tag_names:
            for m in _merged_ids_with_tag(repo, user_repo, tn, pdir):
                if m["id"] in seen:
                    continue
                seen.add(m["id"])
                tags = json.loads(m["tags"]) if isinstance(m.get("tags"), str) else m.get("tags", [])
                new_tags = [t for t in tags if t not in tag_names]
                if len(new_tags) != len(tags):
                    table = "user_memories" if user_repo.get_by_id(m["id"]) else "memories"
                    with cm.get_conn() as conn:
                        conn.execute(f"UPDATE {table} SET tags=%s, updated_at=%s WHERE id=%s",
                                     (json.dumps(new_tags, ensure_ascii=False), repo._now(), m["id"]))
                    updated += 1
        return {"deleted_tags": tag_names, "updated_memories": updated}

    # ── Projects ──

    @app.get("/api/projects")
    async def api_get_projects(request: Request):
        cm = _get_cm(request)
        uid = _user_id(request)
        with cm.get_conn() as conn:
            if uid:
                rows = conn.execute(
                    "SELECT project_dir, COUNT(*) as mem_count FROM memories WHERE user_id=%s GROUP BY project_dir", (uid,)
                ).fetchall()
            else:
                rows = conn.execute("SELECT project_dir, COUNT(*) as mem_count FROM memories GROUP BY project_dir").fetchall()

        projects = {}
        for r in rows:
            pd = r["project_dir"]
            projects.setdefault(pd, {"project_dir": pd, "memories": 0, "issues": 0, "tags": set()})
            projects[pd]["memories"] = r["mem_count"]

        with cm.get_conn() as conn:
            if uid:
                issue_rows = conn.execute("SELECT project_dir, COUNT(*) as cnt FROM issues WHERE user_id=%s GROUP BY project_dir", (uid,)).fetchall()
                archive_rows = conn.execute("SELECT project_dir, COUNT(*) as cnt FROM issues_archive WHERE user_id=%s GROUP BY project_dir", (uid,)).fetchall()
            else:
                issue_rows = conn.execute("SELECT project_dir, COUNT(*) as cnt FROM issues GROUP BY project_dir").fetchall()
                archive_rows = conn.execute("SELECT project_dir, COUNT(*) as cnt FROM issues_archive GROUP BY project_dir").fetchall()

        for r in issue_rows:
            pd = r["project_dir"]
            projects.setdefault(pd, {"project_dir": pd, "memories": 0, "issues": 0, "tags": set()})
            projects[pd]["issues"] += r["cnt"]
        for r in archive_rows:
            pd = r["project_dir"]
            projects.setdefault(pd, {"project_dir": pd, "memories": 0, "issues": 0, "tags": set()})
            projects[pd]["issues"] += r["cnt"]

        with cm.get_conn() as conn:
            if uid:
                state_rows = conn.execute("SELECT project_dir FROM session_state WHERE user_id=%s", (uid,)).fetchall()
            else:
                state_rows = conn.execute("SELECT DISTINCT project_dir FROM session_state").fetchall()
        for r in state_rows:
            pd = r["project_dir"]
            projects.setdefault(pd, {"project_dir": pd, "memories": 0, "issues": 0, "tags": set()})

        with cm.get_conn() as conn:
            if uid:
                tag_rows = conn.execute("SELECT project_dir, tags FROM memories WHERE user_id=%s", (uid,)).fetchall()
            else:
                tag_rows = conn.execute("SELECT project_dir, tags FROM memories").fetchall()
        for r in tag_rows:
            pd = r["project_dir"]
            if pd in projects:
                tags = json.loads(r["tags"]) if isinstance(r["tags"], str) else (r["tags"] or [])
                projects[pd]["tags"].update(tags)

        user_repo = UserMemoryRepo(cm, uid)
        user_tag_counts = user_repo.get_tag_counts()
        user_tags = set(user_tag_counts.keys())
        user_count = user_repo.count()

        result = []
        for pd, info in sorted(projects.items(), key=lambda x: -x[1]["memories"]):
            if not pd:
                continue
            result.append({
                "project_dir": pd,
                "name": pd.replace("\\", "/").rsplit("/", 1)[-1] if pd else "unknown",
                "memories": info["memories"],
                "user_memories": user_count,
                "issues": info["issues"],
                "tags": len(info["tags"] | user_tags),
            })
        return {"projects": result}

    @app.post("/api/projects")
    async def api_add_project(request: Request):
        body = await _read_body(request)
        project_dir = (body.get("project_dir") or "").strip()
        if not project_dir:
            return {"error": "project_dir is required"}
        project_dir = project_dir.replace("\\", "/")
        uid = _user_id(request)
        cm = _get_cm(request)
        now = datetime.now().astimezone().isoformat()
        with cm.get_conn() as conn:
            conn.execute(
                """INSERT INTO session_state (project_dir, user_id, is_blocked, block_reason, next_step, current_task, progress, recent_changes, pending, last_session_id, updated_at)
                   VALUES (%s,%s,false,'','','','[]','[]','[]',1,%s)
                   ON CONFLICT (project_dir, user_id) DO NOTHING""",
                (project_dir, uid, now)
            )
        return {"success": True, "project_dir": project_dir}

    @app.delete("/api/projects/{path:path}")
    async def api_delete_project(path: str, request: Request):
        from urllib.parse import unquote
        project_dir = unquote(path)
        if not project_dir:
            return {"success": False, "error": "Cannot delete empty project"}
        uid = _user_id(request)
        cm = _get_cm(request)
        with cm.get_conn() as conn:
            if uid:
                mem_count = conn.execute("SELECT COUNT(*) as cnt FROM memories WHERE project_dir=%s AND user_id=%s", (project_dir, uid)).fetchone()["cnt"]
                conn.execute("DELETE FROM memories WHERE project_dir=%s AND user_id=%s", (project_dir, uid))
            else:
                mem_count = conn.execute("SELECT COUNT(*) as cnt FROM memories WHERE project_dir=%s", (project_dir,)).fetchone()["cnt"]
                conn.execute("DELETE FROM memories WHERE project_dir=%s", (project_dir,))
            conn.execute("DELETE FROM issues WHERE project_dir=%s", (project_dir,))
            conn.execute("DELETE FROM issues_archive WHERE project_dir=%s", (project_dir,))
            conn.execute("DELETE FROM session_state WHERE project_dir=%s", (project_dir,))
        return {"success": True, "deleted_memories": mem_count}

    @app.get("/api/browse")
    async def api_browse_directory(request: Request):
        params = dict(request.query_params)
        path = (params.get("path") or "").strip()
        if not path:
            path = os.path.expanduser("~")
        path = os.path.expanduser(path)
        if not os.path.isdir(path):
            return {"error": "not a directory", "path": path}
        dirs = []
        try:
            for entry in sorted(os.scandir(path), key=lambda e: e.name.lower()):
                if entry.is_dir() and not entry.name.startswith("."):
                    dirs.append(entry.name)
        except PermissionError:
            return {"error": "permission denied", "path": path}
        return {"path": path.replace("\\", "/"), "dirs": dirs}

    # ── Export / Import ──

    @app.get("/api/export")
    async def api_export_memories(request: Request):
        params = dict(request.query_params)
        scope = params.get("scope", "all")
        pdir = _project_dir(request, params)
        cm = _make_cm(request, pdir)
        repo = MemoryRepo(cm, pdir, cm.user_id)
        user_repo = UserMemoryRepo(cm, cm.user_id)
        if scope == "user":
            memories = user_repo.get_all(limit=999999)
        elif scope == "project":
            memories = repo.get_all(limit=999999, project_dir=pdir)
        else:
            memories = repo.get_all(limit=999999) + user_repo.get_all(limit=999999)
        return {"memories": memories, "count": len(memories), "project_dir": pdir}

    @app.post("/api/import")
    async def api_import_memories(request: Request):
        body = await _read_body(request)
        items = body.get("memories", [])
        if not items:
            return {"error": "no memories to import"}
        params = dict(request.query_params)
        pdir = _project_dir(request, params)
        cm = _make_cm(request, pdir)
        repo = MemoryRepo(cm, pdir, cm.user_id)
        user_repo = UserMemoryRepo(cm, cm.user_id)
        imported, skipped = 0, 0
        for item in items:
            mid = item.get("id", "")
            if not mid or repo.get_by_id(mid) or user_repo.get_by_id(mid):
                skipped += 1
                continue
            now = repo._now()
            tags = item.get("tags", "[]")
            tags_str = json.dumps(tags, ensure_ascii=False) if isinstance(tags, list) else tags
            scope = item.get("scope", "project")
            embedding = item.get("embedding")
            emb_str = str(embedding) if embedding else None
            with cm.get_conn() as conn:
                if scope == "user":
                    conn.execute(
                        """INSERT INTO user_memories (id, content, tags, source, user_id, session_id, embedding, created_at, updated_at)
                           VALUES (%s,%s,%s,%s,%s,%s,%s::vector,%s,%s)""",
                        (mid, item.get("content", ""), tags_str, item.get("source", "manual"),
                         cm.user_id, item.get("session_id", 0), emb_str, item.get("created_at", now), now)
                    )
                else:
                    conn.execute(
                        """INSERT INTO memories (id, content, tags, scope, source, project_dir, user_id, session_id, embedding, created_at, updated_at)
                           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s::vector,%s,%s)""",
                        (mid, item.get("content", ""), tags_str, scope, item.get("source", "manual"),
                         item.get("project_dir", pdir), cm.user_id, item.get("session_id", 0), emb_str,
                         item.get("created_at", now), now)
                    )
            imported += 1
        return {"imported": imported, "skipped": skipped}

    # ── Search ──

    @app.post("/api/search")
    async def api_search_memories(request: Request):
        body = await _read_body(request)
        query = body.get("query", "").strip()
        if not query:
            return {"error": "query required"}
        top_k = body.get("top_k", 20)
        scope = body.get("scope", "all")
        tags = body.get("tags", [])
        params = dict(request.query_params)
        pdir = _project_dir(request, params)
        cm = _make_cm(request, pdir)

        engine = _get_engine(request)
        if not engine:
            return {"error": "embedding engine not loaded"}

        embedding = engine.encode(query)
        repo = MemoryRepo(cm, pdir, cm.user_id)
        user_repo = UserMemoryRepo(cm, cm.user_id)
        team_repo = TeamMemoryRepo(cm, pdir)

        if scope == "user":
            results = user_repo.search_by_vector_with_tags(embedding, tags, top_k=top_k) if tags else user_repo.search_by_vector(embedding, top_k=top_k)
        elif scope == "team":
            results = team_repo.search_by_vector_with_tags(embedding, tags, top_k=top_k) if tags else team_repo.search_by_vector(embedding, top_k=top_k)
        elif scope == "project":
            results = repo.search_by_vector_with_tags(embedding, tags, top_k=top_k, scope="project", project_dir=pdir) if tags else repo.search_by_vector(embedding, top_k=top_k, scope="project", project_dir=pdir)
        else:
            if tags:
                proj_results = repo.search_by_vector_with_tags(embedding, tags, top_k=top_k, scope="project", project_dir=pdir)
                user_results = user_repo.search_by_vector_with_tags(embedding, tags, top_k=top_k)
                team_results = team_repo.search_by_vector_with_tags(embedding, tags, top_k=top_k)
            else:
                proj_results = repo.search_by_vector(embedding, top_k=top_k, scope="project", project_dir=pdir)
                user_results = user_repo.search_by_vector(embedding, top_k=top_k)
                team_results = team_repo.search_by_vector(embedding, top_k=top_k)
            results = sorted(proj_results + user_results + team_results, key=lambda x: x.get("similarity", 0), reverse=True)[:top_k]

        return {"results": results, "count": len(results), "query": query}


# ── Helper functions (outside register_routes) ──

async def _read_body(request: Request) -> dict:
    try:
        return await request.json()
    except Exception:
        return {}


def _merged_tag_counts(mem_repo, user_repo, team_repo, pdir):
    proj = mem_repo.get_tag_counts(project_dir=pdir)
    user = user_repo.get_tag_counts()
    team = _team_tag_counts(mem_repo.cm, pdir)
    merged = dict(proj)
    for k, v in user.items():
        merged[k] = merged.get(k, 0) + v
    for k, v in team.items():
        merged[k] = merged.get(k, 0) + v
    return merged


def _team_tag_counts(cm, pdir) -> dict:
    with cm.get_conn() as conn:
        rows = conn.execute("SELECT tags FROM team_memories WHERE project_dir=%s", (pdir,)).fetchall()
    counts = {}
    for r in rows:
        tag_list = json.loads(r["tags"]) if isinstance(r["tags"], str) else (r["tags"] or [])
        for t in tag_list:
            counts[t] = counts.get(t, 0) + 1
    return counts


def _merged_ids_with_tag(mem_repo, user_repo, tag, pdir):
    proj = mem_repo.get_ids_with_tag(tag, project_dir=pdir)
    user = user_repo.get_ids_with_tag(tag)
    seen = {m["id"] for m in proj}
    return proj + [m for m in user if m["id"] not in seen]
