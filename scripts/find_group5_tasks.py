"""查找 MCP SQLite 中 Group 5 任务 IDs"""
import sqlite3, os, glob

home = os.path.expanduser("~")
db_files = []
for root, dirs, files in os.walk(os.path.join(home, ".aivectormemory")):
    for f in files:
        if f.endswith(".db"):
            db_files.append(os.path.join(root, f))

alt = os.path.join(home, ".aivectormemory.db")
if os.path.exists(alt):
    db_files.append(alt)

if not db_files:
    print("No .db files found")

for db_path in db_files:
    print(f"\n=== {db_path} ===")
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tasks'")
        if not cur.fetchone():
            print("  No tasks table")
            conn.close()
            continue
        cur = conn.execute(
            "SELECT id, title, status, parent_id FROM tasks WHERE title LIKE '5.%' ORDER BY id"
        )
        rows = cur.fetchall()
        for r in rows:
            print(f"  ID={r[0]}  parent={r[3]}  status={r[2]}  title={r[1]}")
        if not rows:
            cur2 = conn.execute("SELECT id, title, status, parent_id FROM tasks ORDER BY id DESC LIMIT 15")
            print("  Last 15 tasks:")
            for r in cur2.fetchall():
                print(f"  ID={r[0]}  parent={r[3]}  status={r[2]}  title={r[1]}")
        conn.close()
    except Exception as e:
        print(f"  Error: {e}")
