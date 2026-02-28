#!/usr/bin/env python3
"""同步数据库中已完成任务到 tasks.md 文件"""
import os
import re
from pathlib import Path

os.environ.setdefault("GATEWAYAIVECTORMEMORY_PG_URL", "postgresql:///gatewayaivectormemory")

from gatewayaivectormemory.db.connection import ConnectionManager

_SPEC_DIRS = [".kiro/specs", ".cursor/specs", ".windsurf/specs", ".trae/specs", "docs/specs"]


def sync_tasks_md():
    pg_url = os.environ.get("GATEWAYAIVECTORMEMORY_PG_URL")
    project_dir = os.getcwd()
    user_id = ""  # 空字符串匹配当前用户

    cm = ConnectionManager(pg_url, project_dir=project_dir, user_id=user_id)

    with cm.get_conn() as conn:
        # 获取所有已完成的任务
        rows = conn.execute(
            "SELECT feature_id, title, status FROM tasks WHERE project_dir=%s AND status='completed'",
            (project_dir,)
        ).fetchall()

    print(f"找到 {len(rows)} 个已完成任务")

    # 按 feature_id 分组
    by_feature = {}
    for r in rows:
        fid = r["feature_id"]
        by_feature.setdefault(fid, []).append(r["title"])

    updated_count = 0
    for feature_id, titles in by_feature.items():
        for spec_dir in _SPEC_DIRS:
            tasks_md = Path(project_dir) / spec_dir / feature_id / "tasks.md"
            if not tasks_md.is_file():
                continue

            text = tasks_md.read_text(encoding="utf-8")
            original = text

            for title in titles:
                escaped = re.escape(title)
                pattern = re.compile(rf"^(- \[ \] ){escaped}\s*$", re.MULTILINE)
                match = pattern.search(text)
                if match:
                    line = match.group(0)
                    new_line = line.replace("- [ ]", "- [x]", 1)
                    text = text.replace(line, new_line, 1)
                    updated_count += 1

            if text != original:
                tasks_md.write_text(text, encoding="utf-8")
                print(f"✅ 更新 {tasks_md}")

    cm.close()
    print(f"\n✅ 同步完成，更新了 {updated_count} 个 checkbox")


if __name__ == "__main__":
    sync_tasks_md()
