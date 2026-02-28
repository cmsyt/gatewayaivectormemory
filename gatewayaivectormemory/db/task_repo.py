from datetime import datetime


def _serialize_row(row: dict) -> dict:
    """Convert datetime fields to ISO strings for JSON serialization"""
    for key in ("created_at", "updated_at", "archived_at"):
        if key in row and hasattr(row[key], "isoformat"):
            row[key] = row[key].isoformat()
    return row


class TaskRepo:
    def __init__(self, conn_manager, project_dir: str = "", user_id: str = ""):
        self.cm = conn_manager
        self.project_dir = project_dir
        self.user_id = user_id

    def _now(self) -> str:
        return datetime.now().astimezone().isoformat()

    def batch_create(self, feature_id: str, tasks: list[dict], task_type: str = "manual") -> dict:
        created, skipped = 0, 0
        now = self._now()
        with self.cm.get_conn() as conn:
            for t in tasks:
                title = t.get("title", "").strip()
                if not title:
                    skipped += 1
                    continue
                parent_id = t.get("parent_id", 0)
                existing = conn.execute(
                    "SELECT id FROM tasks WHERE project_dir=%s AND user_id=%s AND feature_id=%s AND title=%s AND parent_id=%s",
                    (self.project_dir, self.user_id, feature_id, title, parent_id)
                ).fetchone()
                if existing:
                    skipped += 1
                    continue
                cur = conn.execute(
                    """INSERT INTO tasks (project_dir, user_id, feature_id, title, status, sort_order, parent_id, task_type, metadata, created_at, updated_at)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
                    (self.project_dir, self.user_id, feature_id, title, "pending", t.get("sort_order", 0), parent_id, task_type, t.get("metadata", "{}"), now, now)
                )
                node_id = cur.fetchone()["id"]
                created += 1
                for child in t.get("children", []):
                    child_title = child.get("title", "").strip()
                    if not child_title:
                        skipped += 1
                        continue
                    child_existing = conn.execute(
                        "SELECT id FROM tasks WHERE project_dir=%s AND user_id=%s AND feature_id=%s AND title=%s AND parent_id=%s",
                        (self.project_dir, self.user_id, feature_id, child_title, node_id)
                    ).fetchone()
                    if child_existing:
                        skipped += 1
                        continue
                    conn.execute(
                        """INSERT INTO tasks (project_dir, user_id, feature_id, title, status, sort_order, parent_id, task_type, metadata, created_at, updated_at)
                           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                        (self.project_dir, self.user_id, feature_id, child_title, "pending", child.get("sort_order", 0), node_id, task_type, child.get("metadata", "{}"), now, now)
                    )
                    created += 1
        return {"created": created, "skipped": skipped, "feature_id": feature_id}

    def update(self, task_id: int, **fields) -> dict | None:
        with self.cm.get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM tasks WHERE id=%s AND project_dir=%s AND user_id=%s",
                (task_id, self.project_dir, self.user_id)
            ).fetchone()
            if not row:
                return None
            allowed = {"status", "title"}
            updates = {k: v for k, v in fields.items() if k in allowed}
            if not updates:
                return _serialize_row(dict(row))
            updates["updated_at"] = self._now()
            set_clause = ",".join(f"{k}=%s" for k in updates)
            conn.execute(f"UPDATE tasks SET {set_clause} WHERE id=%s", [*updates.values(), task_id])
            return _serialize_row(dict(conn.execute("SELECT * FROM tasks WHERE id=%s", (task_id,)).fetchone()))

    def list_by_feature(self, feature_id: str | None = None, status: str | None = None) -> list[dict]:
        with self.cm.get_conn() as conn:
            sql, params = "SELECT * FROM tasks WHERE project_dir=%s AND user_id=%s", [self.project_dir, self.user_id]
            if feature_id:
                sql += " AND feature_id=%s"
                params.append(feature_id)
            sql += " ORDER BY feature_id, sort_order, id"
            rows = [_serialize_row(dict(r)) for r in conn.execute(sql, params).fetchall()]

        top_level = [r for r in rows if r.get("parent_id", 0) == 0]
        children_map: dict[int, list[dict]] = {}
        for r in rows:
            pid = r.get("parent_id", 0)
            if pid != 0:
                children_map.setdefault(pid, []).append(r)

        result = []
        for node in top_level:
            all_kids = children_map.get(node["id"], [])
            if all_kids:
                kids = [k for k in all_kids if k["status"] == status] if status else all_kids
                if status and not kids:
                    continue
                node["children"] = kids
                node["status"] = self._compute_status(kids)
                result.append(node)
            else:
                node["children"] = []
                if status and node["status"] != status:
                    continue
                result.append(node)
        return result

    def _compute_status(self, children: list[dict]) -> str:
        statuses = {c["status"] for c in children}
        if statuses == {"completed"}:
            return "completed"
        if statuses == {"pending"}:
            return "pending"
        return "in_progress"

    def delete(self, task_id: int) -> dict | None:
        with self.cm.get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM tasks WHERE id=%s AND project_dir=%s AND user_id=%s",
                (task_id, self.project_dir, self.user_id)
            ).fetchone()
            if not row:
                return None
            result = _serialize_row(dict(row))
            conn.execute("DELETE FROM tasks WHERE parent_id=%s AND project_dir=%s AND user_id=%s",
                         (task_id, self.project_dir, self.user_id))
            conn.execute("DELETE FROM tasks WHERE id=%s AND project_dir=%s AND user_id=%s",
                         (task_id, self.project_dir, self.user_id))
        return result

    def delete_by_feature(self, feature_id: str) -> int:
        with self.cm.get_conn() as conn:
            count = conn.execute(
                "SELECT COUNT(*) AS c FROM tasks WHERE project_dir=%s AND user_id=%s AND feature_id=%s",
                (self.project_dir, self.user_id, feature_id)
            ).fetchone()["c"]
            conn.execute(
                "DELETE FROM tasks WHERE project_dir=%s AND user_id=%s AND feature_id=%s",
                (self.project_dir, self.user_id, feature_id)
            )
        return count

    def complete_by_feature(self, feature_id: str):
        now = self._now()
        with self.cm.get_conn() as conn:
            conn.execute(
                "UPDATE tasks SET status='completed', updated_at=%s WHERE project_dir=%s AND user_id=%s AND feature_id=%s AND status!='completed'",
                (now, self.project_dir, self.user_id, feature_id)
            )

    def archive_by_feature(self, feature_id: str) -> dict:
        now = self._now()
        with self.cm.get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM tasks WHERE project_dir=%s AND user_id=%s AND feature_id=%s",
                (self.project_dir, self.user_id, feature_id)
            ).fetchall()
            count = 0
            for r in rows:
                conn.execute(
                    """INSERT INTO tasks_archive
                       (project_dir, user_id, feature_id, title, status, sort_order, parent_id,
                        task_type, metadata, original_task_id, archived_at, created_at, updated_at)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (r["project_dir"], self.user_id, r["feature_id"], r["title"], r["status"],
                     r["sort_order"], r["parent_id"], r["task_type"], r["metadata"],
                     r["id"], now, r["created_at"], r["updated_at"])
                )
                count += 1
            conn.execute(
                "DELETE FROM tasks WHERE project_dir=%s AND user_id=%s AND feature_id=%s",
                (self.project_dir, self.user_id, feature_id)
            )
        return {"archived": count, "feature_id": feature_id}

    def list_archived(self, feature_id: str | None = None) -> list[dict]:
        with self.cm.get_conn() as conn:
            sql, params = "SELECT * FROM tasks_archive WHERE project_dir=%s AND user_id=%s", [self.project_dir, self.user_id]
            if feature_id:
                sql += " AND feature_id=%s"
                params.append(feature_id)
            sql += " ORDER BY feature_id, sort_order, id"
            rows = [_serialize_row(dict(r)) for r in conn.execute(sql, params).fetchall()]

        top_level = [r for r in rows if r["parent_id"] == 0]
        for node in top_level:
            node["children"] = [r for r in rows if r["parent_id"] == node["original_task_id"]]
        return top_level

    def get_feature_status(self, feature_id: str) -> str:
        with self.cm.get_conn() as conn:
            rows = conn.execute(
                "SELECT status FROM tasks WHERE project_dir=%s AND user_id=%s AND feature_id=%s AND parent_id!=0",
                (self.project_dir, self.user_id, feature_id)
            ).fetchall()
            if not rows:
                rows = conn.execute(
                    "SELECT status FROM tasks WHERE project_dir=%s AND user_id=%s AND feature_id=%s",
                    (self.project_dir, self.user_id, feature_id)
                ).fetchall()
        if not rows:
            return "pending"
        statuses = {r["status"] for r in rows}
        if statuses == {"completed"}:
            return "completed"
        if statuses == {"pending"}:
            return "pending"
        return "in_progress"
