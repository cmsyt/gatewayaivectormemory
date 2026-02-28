import json
import uuid
from datetime import datetime


def _serialize_row(row: dict) -> dict:
    """Convert datetime fields to ISO strings for JSON serialization"""
    for key in ("created_at", "updated_at", "archived_at"):
        if key in row and hasattr(row[key], "isoformat"):
            row[key] = row[key].isoformat()
    return row


class MemoryRepo:
    def __init__(self, conn_manager, project_dir: str = "", user_id: str = ""):
        self.cm = conn_manager
        self.project_dir = project_dir
        self.user_id = user_id

    def _now(self) -> str:
        return datetime.now().astimezone().isoformat()

    def insert(self, content: str, tags: list[str], scope: str, session_id: int,
               embedding: list[float], dedup_threshold: float = 0.95,
               source: str = "manual") -> dict:
        dup = self.find_duplicate(embedding, dedup_threshold)
        if dup:
            return self.update(dup["id"], content, tags, session_id, embedding)
        now = self._now()
        mid = uuid.uuid4().hex[:12]
        tags_json = json.dumps(tags, ensure_ascii=False)
        with self.cm.get_conn() as conn:
            conn.execute(
                """INSERT INTO memories (id, content, tags, scope, source, project_dir, user_id, session_id, embedding, created_at, updated_at)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s::vector,%s,%s)""",
                (mid, content, tags_json, scope, source, self.project_dir, self.user_id, session_id, str(embedding), now, now)
            )
        return {"id": mid, "action": "created"}

    def update(self, mid: str, content: str, tags: list[str], session_id: int,
               embedding: list[float]) -> dict:
        now = self._now()
        tags_json = json.dumps(tags, ensure_ascii=False)
        with self.cm.get_conn() as conn:
            conn.execute(
                "UPDATE memories SET content=%s, tags=%s, session_id=%s, embedding=%s::vector, updated_at=%s WHERE id=%s",
                (content, tags_json, session_id, str(embedding), now, mid)
            )
        return {"id": mid, "action": "updated"}

    def find_duplicate(self, embedding: list[float], threshold: float) -> dict | None:
        emb_str = str(embedding)
        with self.cm.get_conn() as conn:
            rows = conn.execute(
                """SELECT id, 1 - (embedding <=> %s::vector) AS similarity
                   FROM memories WHERE project_dir=%s AND user_id=%s AND embedding IS NOT NULL
                   ORDER BY embedding <=> %s::vector LIMIT 5""",
                (emb_str, self.project_dir, self.user_id, emb_str)
            ).fetchall()
        for r in rows:
            if r["similarity"] >= threshold:
                return _serialize_row(dict(r))
        return None

    def search_by_vector(self, embedding: list[float], top_k: int = 5,
                         scope: str = "all", project_dir: str = "",
                         source: str | None = None) -> list[dict]:
        conditions, params = ["user_id=%s"], [self.user_id]
        if scope == "project":
            conditions.append("project_dir=%s")
            params.append(project_dir or self.project_dir)
        if source:
            conditions.append("source=%s")
            params.append(source)
        conditions.append("embedding IS NOT NULL")
        return self._vector_query(embedding, top_k, conditions, params)

    def _vector_query(self, embedding: list[float], top_k: int,
                      conditions: list[str], params: list) -> list[dict]:
        where = " AND ".join(conditions)
        emb_str = str(embedding)
        all_params = [emb_str] + params + [emb_str, top_k]
        sql = f"""SELECT *, 1 - (embedding <=> %s::vector) AS similarity
                  FROM memories WHERE {where}
                  ORDER BY embedding <=> %s::vector LIMIT %s"""
        with self.cm.get_conn() as conn:
            rows = conn.execute(sql, all_params).fetchall()
        return [_serialize_row(dict(r)) for r in rows]

    def search_by_vector_with_tags(self, embedding: list[float], tags: list[str],
                                    top_k: int = 5, scope: str = "all",
                                    project_dir: str = "",
                                    source: str | None = None) -> list[dict]:
        conditions, params = ["user_id=%s"], [self.user_id]
        if scope == "project":
            conditions.append("project_dir=%s")
            params.append(project_dir or self.project_dir)
        if source:
            conditions.append("source=%s")
            params.append(source)
        for tag in tags:
            conditions.append("tags LIKE %s")
            params.append(f'%"{tag}"%')
        conditions.append("embedding IS NOT NULL")
        return self._vector_query(embedding, top_k, conditions, params)

    def delete(self, mid: str) -> bool:
        with self.cm.get_conn() as conn:
            cur = conn.execute("DELETE FROM memories WHERE id=%s AND user_id=%s", (mid, self.user_id))
            return cur.rowcount > 0

    def get_all(self, limit: int = 100, offset: int = 0, project_dir: str | None = None) -> list[dict]:
        conditions, params = ["user_id=%s"], [self.user_id]
        if project_dir is not None:
            conditions.append("project_dir=%s")
            params.append(project_dir)
        where = " AND ".join(conditions)
        params.extend([limit, offset])
        with self.cm.get_conn() as conn:
            rows = conn.execute(
                f"SELECT * FROM memories WHERE {where} ORDER BY created_at DESC LIMIT %s OFFSET %s", params
            ).fetchall()
        return [_serialize_row(dict(r)) for r in rows]

    def get_by_id(self, mid: str) -> dict | None:
        with self.cm.get_conn() as conn:
            row = conn.execute("SELECT * FROM memories WHERE id=%s", (mid,)).fetchone()
        return _serialize_row(dict(row)) if row else None

    def count(self, project_dir: str | None = None) -> int:
        conditions, params = ["user_id=%s"], [self.user_id]
        if project_dir is not None:
            conditions.append("project_dir=%s")
            params.append(project_dir)
        where = " AND ".join(conditions)
        with self.cm.get_conn() as conn:
            row = conn.execute(f"SELECT COUNT(*) AS cnt FROM memories WHERE {where}", params).fetchone()
        return row["cnt"]

    def list_by_tags(self, tags: list[str], scope: str = "all", project_dir: str = "",
                     limit: int = 100, source: str | None = None) -> list[dict]:
        conditions, params = ["user_id=%s"], [self.user_id]
        if scope == "project":
            conditions.append("project_dir=%s")
            params.append(project_dir or self.project_dir)
        if source:
            conditions.append("source=%s")
            params.append(source)
        for tag in tags:
            conditions.append("tags LIKE %s")
            params.append(f'%"{tag}"%')
        where = " AND ".join(conditions)
        params.append(limit)
        with self.cm.get_conn() as conn:
            rows = conn.execute(
                f"SELECT * FROM memories WHERE {where} ORDER BY created_at DESC LIMIT %s", params
            ).fetchall()
        return [_serialize_row(dict(r)) for r in rows]

    def get_tag_counts(self, project_dir: str | None = None) -> dict[str, int]:
        conditions, params = ["user_id=%s"], [self.user_id]
        if project_dir is not None:
            conditions.append("project_dir=%s")
            params.append(project_dir)
        where = " AND ".join(conditions)
        with self.cm.get_conn() as conn:
            rows = conn.execute(f"SELECT tags FROM memories WHERE {where}", params).fetchall()
        counts = {}
        for r in rows:
            tag_list = json.loads(r["tags"]) if isinstance(r["tags"], str) else (r["tags"] or [])
            for t in tag_list:
                counts[t] = counts.get(t, 0) + 1
        return counts

    def get_ids_with_tag(self, tag: str, project_dir: str | None = None) -> list[dict]:
        conditions, params = ["user_id=%s", "tags LIKE %s"], [self.user_id, f'%"{tag}"%']
        if project_dir is not None:
            conditions.append("project_dir=%s")
            params.append(project_dir)
        where = " AND ".join(conditions)
        with self.cm.get_conn() as conn:
            rows = conn.execute(f"SELECT id, tags FROM memories WHERE {where}", params).fetchall()
        return [_serialize_row(dict(r)) for r in rows]
