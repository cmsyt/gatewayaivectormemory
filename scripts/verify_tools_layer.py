#!/usr/bin/env python3
"""验证 tools 层适配 PostgreSQL 后是否正常工作"""
import os
import sys

os.environ.setdefault("GATEWAYAIVECTORMEMORY_PG_URL", "postgresql:///gatewayaivectormemory")

from gatewayaivectormemory.db.connection import ConnectionManager
from gatewayaivectormemory.db.schema import init_db


def test_tools():
    pg_url = os.environ.get("GATEWAYAIVECTORMEMORY_PG_URL")
    if not pg_url:
        print("❌ GATEWAYAIVECTORMEMORY_PG_URL not set")
        return False

    cm = ConnectionManager(pg_url, project_dir="/test/project", user_id="test_user")

    # 初始化数据库
    with cm.get_conn() as conn:
        init_db(conn)

    print("✅ ConnectionManager 创建成功")
    print(f"   project_dir: {cm.project_dir}")
    print(f"   user_id: {cm.user_id}")

    # 测试 StateRepo
    from gatewayaivectormemory.db.state_repo import StateRepo
    state_repo = StateRepo(cm, cm.project_dir, cm.user_id)
    state = state_repo.get()
    print(f"✅ StateRepo.get() 成功: {state is not None or 'None (新用户)'}")

    # 测试 IssueRepo
    from gatewayaivectormemory.db.issue_repo import IssueRepo
    issue_repo = IssueRepo(cm, cm.project_dir, cm.user_id)
    issues, total = issue_repo.list_by_date(brief=True, limit=5)
    print(f"✅ IssueRepo.list_by_date() 成功: {total} issues")

    # 测试 TaskRepo
    from gatewayaivectormemory.db.task_repo import TaskRepo
    task_repo = TaskRepo(cm, cm.project_dir, cm.user_id)
    tasks = task_repo.list_by_feature(feature_id="test-feature")
    print(f"✅ TaskRepo.list_by_feature() 成功: {len(tasks)} tasks")

    # 测试 MemoryRepo
    from gatewayaivectormemory.db.memory_repo import MemoryRepo
    mem_repo = MemoryRepo(cm, cm.project_dir, cm.user_id)
    count = mem_repo.count()
    print(f"✅ MemoryRepo.count() 成功: {count} memories")

    # 测试 UserMemoryRepo
    from gatewayaivectormemory.db.user_memory_repo import UserMemoryRepo
    user_repo = UserMemoryRepo(cm, cm.user_id)
    user_count = user_repo.count()
    print(f"✅ UserMemoryRepo.count() 成功: {user_count} user memories")

    # 测试 TeamMemoryRepo
    from gatewayaivectormemory.db.team_memory_repo import TeamMemoryRepo
    team_repo = TeamMemoryRepo(cm, cm.project_dir)
    team_count = team_repo.count()
    print(f"✅ TeamMemoryRepo.count() 成功: {team_count} team memories")

    cm.close()
    print("\n✅ 所有 Repo 层测试通过")
    return True


if __name__ == "__main__":
    success = test_tools()
    sys.exit(0 if success else 1)
