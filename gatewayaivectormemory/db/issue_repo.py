import json
from datetime import datetime


def _serialize_row(row: dict) -> dict:
    """Convert datetime fields to ISO strings for JSON serialization"""
    for key in ("created_at", "updated_at", "archived_at"):
        if key in row and hasattr(row[key], "isoformat"):
            row[key] = row[key].isoformat()
    return row


class IssueRepo:
    def __init__(self, conn_manager, project_dir: str = "", user_id: str = "", engine=None):
        self.cm = conn_manager
        self.project_dir = project_dir
        self.user_id = user_id
        self.engine = engine

    def _now(self) -> str:
        return datetime.now().astimezone().isoformat()

    def _next_number(self) -> int:
        with self.cm.get_conn() as conn:
            r1 = conn.execute(
                "SELECT MAX(issue_number) AS m FROM issues WHERE project_dir=%s AND user_id=%s",
                (self.project_dir, self.user_id)
            ).fetchone()
            r2 = conn.execute(
                "SELECT MAX(issue_number) AS m FROM issues_archive WHERE project_dir=%s AND user_id=%s",
                (self.project_dir, self.user_id)
            ).fetchone()
        return max(r1["m"] or 0, r2["m"] or 0) + 1

    def get_by_number(self, num: int) -> dict | None:
        with self.cm.get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM issues WHERE issue_number=%s AND project_dir=%s AND user_id=%s",
                (num, self.project_dir, self.user_id)
            ).fetchone()
        return _serialize_row(dict(row)) if row else None

    def get_archived_by_number(self, num: int) -> dict | None:
        with self.cm.get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM issues_archive WHERE issue_number=%s AND project_dir=%s AND user_id=%s",
                (num, self.project_dir, self.user_id)
            ).fetchone()
        return _serialize_row(dict(row)) if row else None

    def create(self, date: str, title: str, content: str = "", memory_id: str = "", parent_id: int = 0) -> dict:
        with self.cm.get_conn() as conn:
            existing = conn.execute(
                "SELECT * FROM issues WHERE project_dir=%s AND user_id=%s AND title=%s AND status!='archived'",
                (self.project_dir, self.user_id, title)
            ).fetchone()
            if existing:
                return {"id": existing["id"], "issue_number": existing["issue_number"], "date": existing["date"], "deduplicated": True}
            now = self._now()
            num = self._next_number()
            cur = conn.execute(
                """INSERT INTO issues (project_dir, user_id, issue_number, date, title, status, content, memory_id, parent_id, created_at, updated_at)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
                (self.project_dir, self.user_id, num, date, title, "pending", content, memory_id, parent_id, now, now)
            )
            new_id = cur.fetchone()["id"]
        return {"id": new_id, "issue_number": num, "date": date}

    def update(self, issue_id: int, **fields) -> dict | None:
        with self.cm.get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM issues WHERE id=%s AND project_dir=%s AND user_id=%s",
                (issue_id, self.project_dir, self.user_id)
            ).fetchone()
            if not row:
                return None
            allowed = {"title", "status", "content", "memory_id",
                       "description", "investigation", "root_cause", "solution",
                       "files_changed", "test_result", "notes", "feature_id"}
            updates = {k: v for k, v in fields.items() if k in allowed}
            if not updates:
                return _serialize_row(dict(row))
            updates["updated_at"] = self._now()
            set_clause = ",".join(f"{k}=%s" for k in updates)
            conn.execute(
                f"UPDATE issues SET {set_clause} WHERE id=%s",
                [*updates.values(), issue_id]
            )
            return _serialize_row(dict(conn.execute("SELECT * FROM issues WHERE id=%s", (issue_id,)).fetchone()))

    def archive(self, issue_id: int) -> dict | None:
        with self.cm.get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM issues WHERE id=%s AND project_dir=%s AND user_id=%s",
                (issue_id, self.project_dir, self.user_id)
            ).fetchone()
            if not row:
                return None
            now = self._now()
            r = dict(row)
            cur = conn.execute(
                """INSERT INTO issues_archive
                   (project_dir, user_id, issue_number, date, title, content, memory_id,
                    description, investigation, root_cause, solution, files_changed, test_result, notes,
                    feature_id, parent_id, status, original_issue_id, archived_at, created_at)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
                (r["project_dir"], self.user_id, r["issue_number"], r["date"], r["title"], r["content"],
                 r.get("memory_id", ""),
                 r.get("description", ""), r.get("investigation", ""), r.get("root_cause", ""),
                 r.get("solution", ""), r.get("files_changed", "[]"), r.get("test_result", ""),
                 r.get("notes", ""), r.get("feature_id", ""), r.get("parent_id", 0),
                 r.get("status", ""), issue_id, now, r["created_at"])
            )
            archive_id = cur.fetchone()["id"]
            if self.engine:
                text = f"{r['title']} {r.get('description','')} {r.get('root_cause','')} {r.get('solution','')}"
                emb = self.engine.encode(text)
                conn.execute(
                    "UPDATE issues_archive SET embedding=%s::vector WHERE id=%s",
                    (str(emb), archive_id)
                )
            conn.execute("DELETE FROM issues WHERE id=%s", (issue_id,))
        return {"issue_id": issue_id, "archived_at": now, "memory_id": r.get("memory_id", "")}

    _BRIEF_COLS = "id, issue_number, date, title, status, feature_id, created_at"

    def list_by_date(self, date: str | None = None, status: str | None = None,
                     brief: bool = True, limit: int = 50, offset: int = 0,
                     keyword: str | None = None) -> tuple[list[dict], int]:
        cols = self._BRIEF_COLS if brief else "*"
        where, params = "WHERE project_dir=%s AND user_id=%s", [self.project_dir, self.user_id]
        if date:
            where += " AND date=%s"
            params.append(date)
        if status:
            where += " AND status=%s"
            params.append(status)
        if keyword:
            where += " AND title LIKE %s"
            params.append(f"%{keyword}%")
        with self.cm.get_conn() as conn:
            total = conn.execute(f"SELECT COUNT(*) AS c FROM issues {where}", params).fetchone()["c"]
            sql = f"SELECT {cols} FROM issues {where} ORDER BY date DESC, issue_number ASC LIMIT %s OFFSET %s"
            rows = [_serialize_row(dict(r)) for r in conn.execute(sql, params + [limit, offset]).fetchall()]
        return rows, total

    def list_all(self, date: str | None = None, keyword: str | None = None,
                 limit: int = 50, offset: int = 0) -> tuple[list[dict], int]:
        cols = "id, issue_number, date, title, status, feature_id, created_at"
        w1, p1 = "WHERE project_dir=%s AND user_id=%s", [self.project_dir, self.user_id]
        w2, p2 = "WHERE project_dir=%s AND user_id=%s", [self.project_dir, self.user_id]
        if date:
            w1 += " AND date=%s"; w2 += " AND date=%s"
            p1.append(date); p2.append(date)
        if keyword:
            w1 += " AND title LIKE %s"; w2 += " AND title LIKE %s"
            p1.append(f"%{keyword}%"); p2.append(f"%{keyword}%")
        with self.cm.get_conn() as conn:
            cnt = (f"SELECT COUNT(*) AS c FROM ("
                   f"SELECT id FROM issues {w1} UNION ALL "
                   f"SELECT id FROM issues_archive {w2}) sub")
            total = conn.execute(cnt, p1 + p2).fetchone()["c"]
            sql = (f"SELECT {cols}, NULL AS archived_at FROM issues {w1} UNION ALL "
                   f"SELECT {cols}, archived_at FROM issues_archive {w2} "
                   f"ORDER BY date DESC, issue_number ASC LIMIT %s OFFSET %s")
            rows = [_serialize_row(dict(r)) for r in conn.execute(sql, p1 + p2 + [limit, offset]).fetchall()]
        for r in rows:
            if r.get("archived_at"):
                r["status"] = "archived"
        return rows, total

    _BRIEF_COLS_ARCHIVE = "id, issue_number, date, title, status, feature_id, created_at, archived_at"

    def list_archived(self, date: str | None = None, brief: bool = True,
                      limit: int = 50, offset: int = 0,
                      keyword: str | None = None) -> tuple[list[dict], int]:
        cols = self._BRIEF_COLS_ARCHIVE if brief else "*"
        where, params = "WHERE project_dir=%s AND user_id=%s", [self.project_dir, self.user_id]
        if date:
            where += " AND date=%s"
            params.append(date)
        if keyword:
            where += " AND title LIKE %s"
            params.append(f"%{keyword}%")
        with self.cm.get_conn() as conn:
            total = conn.execute(f"SELECT COUNT(*) AS c FROM issues_archive {where}", params).fetchone()["c"]
            sql = f"SELECT {cols} FROM issues_archive {where} ORDER BY date DESC, issue_number ASC LIMIT %s OFFSET %s"
            rows = [_serialize_row(dict(r)) for r in conn.execute(sql, params + [limit, offset]).fetchall()]
        return rows, total

    def get_by_id(self, issue_id: int) -> dict | None:
        with self.cm.get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM issues WHERE id=%s AND project_dir=%s AND user_id=%s",
                (issue_id, self.project_dir, self.user_id)
            ).fetchone()
        return _serialize_row(dict(row)) if row else None

    def get_archived_by_id(self, issue_id: int) -> dict | None:
        with self.cm.get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM issues_archive WHERE original_issue_id=%s AND project_dir=%s AND user_id=%s",
                (issue_id, self.project_dir, self.user_id)
            ).fetchone()
            if not row:
                row = conn.execute(
                    "SELECT * FROM issues_archive WHERE id=%s AND project_dir=%s AND user_id=%s",
                    (issue_id, self.project_dir, self.user_id)
                ).fetchone()
        return _serialize_row(dict(row)) if row else None

    def delete(self, issue_id: int) -> dict | None:
        with self.cm.get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM issues WHERE id=%s AND project_dir=%s AND user_id=%s",
                (issue_id, self.project_dir, self.user_id)
            ).fetchone()
            if not row:
                return None
            memory_id = row.get("memory_id", "")
            conn.execute("DELETE FROM issues WHERE id=%s", (issue_id,))
        return {"issue_id": issue_id, "deleted": True, "memory_id": memory_id}

    def delete_archived(self, archive_id: int) -> dict | None:
        with self.cm.get_conn() as conn:
            row = conn.execute(
                "SELECT * FROM issues_archive WHERE id=%s AND project_dir=%s AND user_id=%s",
                (archive_id, self.project_dir, self.user_id)
            ).fetchone()
            if not row:
                return None
            memory_id = row.get("memory_id", "")
            conn.execute("DELETE FROM issues_archive WHERE id=%s", (archive_id,))
        return {"archive_id": archive_id, "deleted": True, "memory_id": memory_id}

    def search_archive_by_vector(self, embedding: list[float], top_k: int = 5) -> list[dict]:
        emb_str = str(embedding)
        with self.cm.get_conn() as conn:
            rows = conn.execute(
                """SELECT *, 1 - (embedding <=> %s::vector) AS similarity
                   FROM issues_archive WHERE project_dir=%s AND user_id=%s AND embedding IS NOT NULL
                   ORDER BY embedding <=> %s::vector LIMIT %s""",
                (emb_str, self.project_dir, self.user_id, emb_str, top_k)
            ).fetchall()
        return [_serialize_row(dict(r)) for r in rows]

    def list_by_feature_id(self, feature_id: str) -> list[dict]:
        with self.cm.get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM issues WHERE project_dir=%s AND user_id=%s AND feature_id=%s",
                (self.project_dir, self.user_id, feature_id)
            ).fetchall()
        return [_serialize_row(dict(r)) for r in rows]

    def count_active_by_feature(self, feature_id: str) -> int:
        with self.cm.get_conn() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS c FROM issues WHERE project_dir=%s AND user_id=%s AND feature_id=%s",
                (self.project_dir, self.user_id, feature_id)
            ).fetchone()
        return row["c"]
