import json
from datetime import datetime


class StateRepo:
    def __init__(self, conn_manager, project_dir: str = "", user_id: str = ""):
        self.cm = conn_manager
        self.project_dir = project_dir
        self.user_id = user_id

    def _now(self) -> str:
        return datetime.now().astimezone().isoformat()

    def get(self) -> dict | None:
        with self.cm.get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM session_state WHERE project_dir=%s AND user_id=%s",
                (self.project_dir, self.user_id)
            ).fetchone()
        if not row:
            return None
        d = dict(row)
        for key in ("progress", "recent_changes", "pending"):
            d[key] = json.loads(d[key]) if isinstance(d[key], str) else (d[key] or [])
        d["is_blocked"] = bool(d["is_blocked"])
        if d.get("updated_at") and hasattr(d["updated_at"], "isoformat"):
            d["updated_at"] = d["updated_at"].isoformat()
        return d

    def get_session_id(self) -> int:
        with self.cm.get_conn() as conn:
            row = conn.execute(
                "SELECT last_session_id FROM session_state WHERE project_dir=%s AND user_id=%s",
                (self.project_dir, self.user_id)
            ).fetchone()
        return row["last_session_id"] if row else 0

    def upsert(self, **fields) -> dict:
        now = self._now()

        for key in ("progress", "recent_changes", "pending"):
            if key in fields and isinstance(fields[key], list):
                fields[key] = json.dumps(fields[key], ensure_ascii=False)

        if "is_blocked" in fields:
            fields["is_blocked"] = bool(fields["is_blocked"])

        current = self.get()
        if not current:
            cols = {
                "project_dir": self.project_dir, "user_id": self.user_id,
                "is_blocked": False, "block_reason": "", "next_step": "",
                "current_task": "", "progress": "[]", "recent_changes": "[]",
                "pending": "[]", "last_session_id": 1, "updated_at": now,
            }
            cols.update(fields)
            cols["updated_at"] = now
            col_names = ",".join(cols.keys())
            placeholders = ",".join(["%s"] * len(cols))
            with self.cm.get_conn() as conn:
                conn.execute(
                    f"INSERT INTO session_state ({col_names}) VALUES ({placeholders})",
                    list(cols.values())
                )
        else:
            if not fields:
                return self.get()
            fields["updated_at"] = now
            set_clause = ",".join(f"{k}=%s" for k in fields)
            with self.cm.get_conn() as conn:
                conn.execute(
                    f"UPDATE session_state SET {set_clause} WHERE project_dir=%s AND user_id=%s",
                    [*fields.values(), self.project_dir, self.user_id]
                )
        return self.get()

    def increment_session(self) -> int:
        current = self.get_session_id()
        new_id = current + 1
        self.upsert(last_session_id=new_id)
        return new_id
