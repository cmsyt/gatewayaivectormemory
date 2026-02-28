"""PostgreSQL schema verification script for gateway-postgresql-mode."""
import os
import sys

def main():
    pg_url = os.environ.get("GATEWAYAIVECTORMEMORY_PG_URL", "postgresql:///gatewayaivectormemory")
    print(f"Connecting to: {pg_url}")

    try:
        import psycopg
        from psycopg.rows import dict_row
    except ImportError:
        print("ERROR: psycopg not installed. Run: pip install 'psycopg[binary]'")
        sys.exit(1)

    try:
        conn = psycopg.connect(pg_url, row_factory=dict_row)
    except Exception as e:
        print(f"ERROR: Cannot connect to PostgreSQL: {e}")
        sys.exit(1)

    # 1. Init schema
    from gatewayaivectormemory.db.schema import init_db
    init_db(conn)
    print("✓ Schema initialized")

    # 2. Check pgvector extension
    row = conn.execute("SELECT extname FROM pg_extension WHERE extname='vector'").fetchone()
    assert row, "pgvector extension not found"
    print("✓ pgvector extension enabled")

    # 3. Check all tables exist
    expected_tables = [
        "schema_version", "memories", "user_memories", "team_memories",
        "session_state", "issues", "issues_archive", "tasks", "tasks_archive"
    ]
    for table in expected_tables:
        row = conn.execute(
            "SELECT tablename FROM pg_tables WHERE schemaname='public' AND tablename=%s",
            (table,)
        ).fetchone()
        assert row, f"Table {table} not found"
    print(f"✓ All {len(expected_tables)} tables exist")

    # 4. Check vector columns
    vector_cols = [
        ("memories", "embedding"),
        ("user_memories", "embedding"),
        ("team_memories", "embedding"),
    ]
    for table, col in vector_cols:
        row = conn.execute(
            "SELECT udt_name FROM information_schema.columns WHERE table_name=%s AND column_name=%s",
            (table, col)
        ).fetchone()
        assert row and row["udt_name"] == "vector", f"{table}.{col} is not vector type"
    print("✓ Vector columns verified")

    # 5. Check user_id columns
    user_id_tables = ["memories", "user_memories", "session_state", "issues", "issues_archive", "tasks", "tasks_archive"]
    for table in user_id_tables:
        row = conn.execute(
            "SELECT column_name FROM information_schema.columns WHERE table_name=%s AND column_name='user_id'",
            (table,)
        ).fetchone()
        assert row, f"{table} missing user_id column"
    print("✓ user_id columns verified")

    # 6. Check session_state UNIQUE constraint
    row = conn.execute("""
        SELECT constraint_name FROM information_schema.table_constraints
        WHERE table_name='session_state' AND constraint_type='UNIQUE'
    """).fetchone()
    assert row, "session_state UNIQUE constraint not found"
    print("✓ session_state UNIQUE(project_dir, user_id) constraint verified")

    # 7. Check team_memories has created_by
    row = conn.execute(
        "SELECT column_name FROM information_schema.columns WHERE table_name='team_memories' AND column_name='created_by'"
    ).fetchone()
    assert row, "team_memories missing created_by column"
    print("✓ team_memories.created_by column verified")

    # 8. Check indexes
    idx_count = conn.execute(
        "SELECT COUNT(*) AS c FROM pg_indexes WHERE schemaname='public' AND indexname LIKE 'idx_%%'"
    ).fetchone()["c"]
    print(f"✓ {idx_count} custom indexes found")

    conn.close()
    print("\n✅ All schema verifications passed!")

if __name__ == "__main__":
    main()
