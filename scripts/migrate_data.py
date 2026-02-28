"""从 ~/.gatewayaivectormemory/memory.db 读取数据，显示需要迁移的内容"""
import sqlite3
import json
import os

src = os.path.expanduser("~/.gatewayaivectormemory/memory.db")
if not os.path.exists(src):
    print(f"源数据库不存在: {src}")
    exit(1)

conn = sqlite3.connect(src)
conn.row_factory = sqlite3.Row

# 查看所有表
tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
print(f"表: {tables}\n")

# memories (project scope)
rows = conn.execute("SELECT * FROM memories").fetchall()
print(f"=== memories ({len(rows)} 条) ===")
for r in rows:
    print(f"  id={r['id']}, tags={r['tags']}, content={r['content'][:80]}...")

# user_memories
rows = conn.execute("SELECT * FROM user_memories").fetchall()
print(f"\n=== user_memories ({len(rows)} 条) ===")
for r in rows:
    print(f"  id={r['id']}, tags={r['tags']}, content={r['content'][:80]}...")

# issues
rows = conn.execute("SELECT * FROM issues").fetchall()
print(f"\n=== issues ({len(rows)} 条) ===")
for r in rows:
    keys = r.keys()
    print(f"  id={r['id']}, title={r['title']}, status={r['status']}")
    if 'content' in keys and r['content']:
        print(f"    content={r['content'][:100]}")

# issues_archive
try:
    rows = conn.execute("SELECT * FROM issues_archive").fetchall()
    print(f"\n=== issues_archive ({len(rows)} 条) ===")
    for r in rows:
        print(f"  id={r['id']}, title={r['title']}")
except:
    print("\n=== issues_archive: 表不存在 ===")

# session_state
rows = conn.execute("SELECT * FROM session_state").fetchall()
print(f"\n=== session_state ({len(rows)} 条) ===")
for r in rows:
    keys = r.keys()
    print(f"  project_dir={r['project_dir']}")
    print(f"  is_blocked={r['is_blocked']}, block_reason={r['block_reason']}")
    print(f"  current_task={r['current_task']}")

# tasks
try:
    rows = conn.execute("SELECT * FROM tasks").fetchall()
    print(f"\n=== tasks ({len(rows)} 条) ===")
    for r in rows:
        print(f"  id={r['id']}, title={r['title']}, status={r['status']}")
except:
    print("\n=== tasks: 表不存在 ===")

conn.close()
