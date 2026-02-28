import psycopg
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool


class ConnectionManager:
    def __init__(self, pg_url: str, project_dir: str = "", user_id: str = ""):
        self.pg_url = pg_url
        self.project_dir = project_dir
        self.user_id = user_id
        self._pool: ConnectionPool | None = None

    def _get_pool(self) -> ConnectionPool:
        if not self._pool:
            self._pool = ConnectionPool(
                self.pg_url,
                min_size=2,
                max_size=10,
                kwargs={"row_factory": dict_row},
            )
        return self._pool

    @property
    def pool(self) -> ConnectionPool:
        return self._get_pool()

    def get_conn(self):
        return self.pool.connection()

    def close(self):
        if self._pool:
            self._pool.close()
            self._pool = None
