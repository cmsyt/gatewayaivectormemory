import json
from gatewayaivectormemory.db.state_repo import StateRepo
from gatewayaivectormemory.db.issue_repo import IssueRepo
from gatewayaivectormemory.db.task_repo import TaskRepo
from gatewayaivectormemory.errors import success_response


def _build_progress(cm) -> list[str]:
    progress = []
    issues, _ = IssueRepo(cm, cm.project_dir, cm.user_id).list_by_date(brief=True, limit=50)
    if issues:
        for i in issues:
            progress.append(f"[track #{i['issue_number']}] {i['title']} ({i['status']})")

    with cm.get_conn() as conn:
        tasks_rows = conn.execute(
            "SELECT DISTINCT feature_id FROM tasks WHERE project_dir=%s AND user_id=%s AND status!='completed'",
            (cm.project_dir, cm.user_id)
        ).fetchall()
        for row in tasks_rows:
            fid = row["feature_id"]
            total = conn.execute(
                "SELECT COUNT(*) as c FROM tasks WHERE project_dir=%s AND user_id=%s AND feature_id=%s",
                (cm.project_dir, cm.user_id, fid)
            ).fetchone()["c"]
            done = conn.execute(
                "SELECT COUNT(*) as c FROM tasks WHERE project_dir=%s AND user_id=%s AND feature_id=%s AND status='completed'",
                (cm.project_dir, cm.user_id, fid)
            ).fetchone()["c"]
            progress.append(f"[task {fid}] {done}/{total} completed")
    return progress


def handle_status(args, *, cm, **_):
    repo = StateRepo(cm, cm.project_dir, cm.user_id)
    state_update = args.get("state")
    clear_fields = args.get("clear_fields") or []

    # clear_fields 合并到 state_update
    if clear_fields:
        state_update = state_update or {}
        allowed = {"recent_changes", "pending"}
        for f in clear_fields:
            if f in allowed and f not in state_update:
                state_update[f] = []

    if state_update:
        if isinstance(state_update, str):
            state_update = json.loads(state_update)
        state_update.pop("progress", None)
        result = repo.upsert(**state_update)
        result["progress"] = _build_progress(cm)
        return json.dumps(success_response(state=result, action="updated"))
    else:
        state = repo.get()
        if not state:
            state = repo.upsert()
        state["progress"] = _build_progress(cm)
        return json.dumps(success_response(state=state, action="read"))
