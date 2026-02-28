import json
import uuid
from datetime import datetime


def _serialize_row(row: dict) -> dict:
    """Convert datetime fields to ISO strings for JSON serialization"""
    for key in ("created_at", "updated_at", "archived_at"):
        if key in row and hasattr(row[key], "isoformat"):
            row[key] = row[key].isoformat()
    return row


class TeamMemoryRepo:
    def __init__(self, conn_manager, project_dir: str = ""):
        self.cm = conn_manager
        self.project_dir = project_dir

    def _now(self) -> str:
        return datetime.now().astimezone().isoformat()

    def insert(self, content: str, tags: list[str], created_by: str, session_id: int,
               embedding: list[float], dedup_threshold: float = 0.95,
               source: str = "manual") -> dict:
        dup = self._find_duplicate(embedding, dedup_threshold)
        if dup:
            return self._update(dup["id"], content, tags, session_id, embedding)
        now = self._now()
        mid = uuid.uuid4().hex[:12]
        tags_json = json.dumps(tags, ensure_ascii=False)
        with self.cm.get_conn() as conn:
            conn.execute(
                """INSERT INTO team_memories (id, content, tags, source, project_dir, created_by, session_id, embedding, created_at, updated_at)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s::vector,%s,%s)""",
                (mid, content, tags_json, source, self.project_dir, created_by, session_id, str(embedding), now, now)
            )
        return {"id": mid, "action": "created"}

    def _update(self, mid: str, content: str, tags: list[str], session_id: int,
                embedding: list[float]) -> dict:
        now = self._now()
        tags_json = json.dumps(tags, ensure_ascii=False)
        with self.cm.get_conn() as conn:
            conn.execute(
                "UPDATE team_memories SET content=%s, tags=%s, session_id=%s, embedding=%s::vector, updated_at=%s WHERE id=%s",
                (content, tags_json, session_id, str(embedding), now, mid)
            )
        return {"id": mid, "action": "updated"}

    def _find_duplicate(self, embedding: list[float], threshold: float) -> dict | None:
        emb_str = str(embedding)
        with self.cm.get_conn() as conn:
            rows = conn.execute(
                """SELECT id, 1 - (embedding <=> %s::vector) AS similarity
                   FROM team_memories WHERE project_dir=%s AND embedding IS NOT NULL
                   ORDER BY embedding <=> %s::vector LIMIT 5""",
                (emb_str, self.project_dir, emb_str)
            ).fetchall()
        for r in rows:
            if r["similarity"] >= threshold:
                return _serialize_row(dict(r))
        return None

    def search_by_vector(self, embedding: list[float], top_k: int = 5) -> list[dict]:
        emb_str = str(embedding)
        with self.cm.get_conn() as conn:
            rows = conn.execute(
                """SELECT *, 1 - (embedding <=> %s::vector) AS similarity
                   FROM team_memories WHERE project_dir=%s AND embedding IS NOT NULL
                   ORDER BY embedding <=> %s::vector LIMIT %s""",
                (emb_str, self.project_dir, emb_str, top_k)
            ).fetchall()
        return [_serialize_row(dict(r)) for r in rows]

    def search_by_vector_with_tags(self, embedding: list[float], tags: list[str],
                                    top_k: int = 5) -> list[dict]:
        conditions, params = ["project_dir=%s", "embedding IS NOT NULL"], [self.project_dir]
        for tag in tags:
            conditions.append("tags LIKE %s")
            params.append(f'%"{tag}"%')
        where = " AND ".join(conditions)
        emb_str = str(embedding)
        params.extend([emb_str, emb_str, top_k])
        sql = f"""SELECT *, 1 - (embedding <=> %s::vector) AS similarity
                  FROM team_memories WHERE {where}
                  ORDER BY embedding <=> %s::vector LIMIT %s"""
        with self.cm.get_conn() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [_serialize_row(dict(r)) for r in rows]

    def delete(self, mid: str) -> bool:
        with self.cm.get_conn() as conn:
            cur = conn.execute("DELETE FROM team_memories WHERE id=%s AND project_dir=%s", (mid, self.project_dir))
            return cur.rowcount > 0

    def list_by_tags(self, tags: list[str], limit: int = 100) -> list[dict]:
        conditions, params = ["project_dir=%s"], [self.project_dir]
        for tag in tags:
            conditions.append("tags LIKE %s")
            params.append(f'%"{tag}"%')
        where = " AND ".join(conditions)
        params.append(limit)
        with self.cm.get_conn() as conn:
            rows = conn.execute(
                f"SELECT * FROM team_memories WHERE {where} ORDER BY created_at DESC LIMIT %s", params
            ).fetchall()
        return [_serialize_row(dict(r)) for r in rows]

    def get_all(self, limit: int = 100, offset: int = 0) -> list[dict]:
        with self.cm.get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM team_memories WHERE project_dir=%s ORDER BY created_at DESC LIMIT %s OFFSET %s",
                (self.project_dir, limit, offset)
            ).fetchall()
        return [_serialize_row(dict(r)) for r in rows]

    def count(self) -> int:
        with self.cm.get_conn() as conn:
            row = conn.execute("SELECT COUNT(*) AS cnt FROM team_memories WHERE project_dir=%s", (self.project_dir,)).fetchone()
        return row["cnt"]
