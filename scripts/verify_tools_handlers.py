#!/usr/bin/env python3
"""验证 tools handler 完整调用链（模拟 MCP 调用）"""
import os
import sys
import json

os.environ.setdefault("GATEWAYAIVECTORMEMORY_PG_URL", "postgresql:///gatewayaivectormemory")

from gatewayaivectormemory.db.connection import ConnectionManager
from gatewayaivectormemory.db.schema import init_db


def test_handlers():
    pg_url = os.environ.get("GATEWAYAIVECTORMEMORY_PG_URL")
    cm = ConnectionManager(pg_url, project_dir="/test/verify_handlers", user_id="test_handler_user")
    
    with cm.get_conn() as conn:
        init_db(conn)
    
    print("=" * 60)
    print("验证 tools handler 完整调用链")
    print("=" * 60)
    
    # 1. 测试 status handler
    print("\n[1] 测试 handle_status...")
    from gatewayaivectormemory.tools.status import handle_status
    result = json.loads(handle_status({}, cm=cm))
    assert result["success"], f"status failed: {result}"
    print(f"    ✅ handle_status() 成功")
    
    # 2. 测试 track handler
    print("\n[2] 测试 handle_track...")
    from gatewayaivectormemory.tools.track import handle_track
    
    # 创建 engine mock（不需要真实 embedding）
    class MockEngine:
        def embed(self, text):
            return [0.1] * 384
        def encode(self, text):
            return [0.1] * 384
    
    result = json.loads(handle_track(
        {"action": "create", "title": "测试问题", "content": "测试内容"},
        cm=cm, engine=MockEngine()
    ))
    assert result["success"], f"track create failed: {result}"
    issue_id = result.get("issue", {}).get("id")
    print(f"    ✅ handle_track(create) 成功, issue_id={issue_id}")
    
    # list
    result = json.loads(handle_track({"action": "list"}, cm=cm, engine=MockEngine()))
    assert result["success"], f"track list failed: {result}"
    print(f"    ✅ handle_track(list) 成功, total={result.get('total', 0)}")
    
    # 3. 测试 task handler
    print("\n[3] 测试 handle_task...")
    from gatewayaivectormemory.tools.task import handle_task
    
    # batch_create
    result = json.loads(handle_task({
        "action": "batch_create",
        "feature_id": "test-feature-handlers",
        "tasks": [{"title": "测试任务1"}, {"title": "测试任务2"}]
    }, cm=cm))
    assert result["success"], f"task batch_create failed: {result}"
    print(f"    ✅ handle_task(batch_create) 成功")
    
    # list
    result = json.loads(handle_task({
        "action": "list",
        "feature_id": "test-feature-handlers"
    }, cm=cm))
    assert result["success"], f"task list failed: {result}"
    tasks = result.get("tasks", [])
    print(f"    ✅ handle_task(list) 成功, count={len(tasks)}")
    
    # update (测试 _sync_tasks_md 和 IssueRepo 联动)
    if tasks:
        task_id = tasks[0]["id"]
        result = json.loads(handle_task({
            "action": "update",
            "task_id": task_id,
            "status": "completed"
        }, cm=cm))
        assert result["success"], f"task update failed: {result}"
        print(f"    ✅ handle_task(update) 成功")
    
    # 4. 测试 remember handler
    print("\n[4] 测试 handle_remember...")
    from gatewayaivectormemory.tools.remember import handle_remember
    result = json.loads(handle_remember({
        "content": "测试记忆内容",
        "tags": ["test", "verify"],
        "scope": "project"
    }, cm=cm, engine=MockEngine(), session_id=1))
    assert result["success"], f"remember failed: {result}"
    print(f"    ✅ handle_remember() 成功")
    
    # 5. 测试 recall handler
    print("\n[5] 测试 handle_recall...")
    from gatewayaivectormemory.tools.recall import handle_recall
    result = json.loads(handle_recall({
        "query": "测试",
        "scope": "project",
        "top_k": 5
    }, cm=cm, engine=MockEngine()))
    assert result["success"], f"recall failed: {result}"
    print(f"    ✅ handle_recall() 成功, count={len(result.get('memories', []))}")
    
    # 6. 测试 forget handler
    print("\n[6] 测试 handle_forget...")
    from gatewayaivectormemory.tools.forget import handle_forget
    result = json.loads(handle_forget({
        "tags": ["test", "verify"],
        "scope": "project"
    }, cm=cm))
    assert result["success"], f"forget failed: {result}"
    print(f"    ✅ handle_forget() 成功")
    
    # 7. 测试 auto_save handler
    print("\n[7] 测试 handle_auto_save...")
    from gatewayaivectormemory.tools.auto_save import handle_auto_save
    result = json.loads(handle_auto_save({
        "preferences": ["测试偏好1", "测试偏好2"]
    }, cm=cm, engine=MockEngine(), session_id=1))
    assert result["success"], f"auto_save failed: {result}"
    print(f"    ✅ handle_auto_save() 成功")
    
    # 8. 测试 team scope
    print("\n[8] 测试 team scope...")
    # remember team
    result = json.loads(handle_remember({
        "content": "团队共享记忆测试",
        "tags": ["team-test"],
        "scope": "team"
    }, cm=cm, engine=MockEngine(), session_id=1))
    assert result["success"], f"remember team failed: {result}"
    team_mem_id = result["id"]
    print(f"    ✅ handle_remember(scope=team) 成功, id={team_mem_id}")
    
    # recall team
    result = json.loads(handle_recall({
        "query": "团队共享",
        "scope": "team",
        "top_k": 5
    }, cm=cm, engine=MockEngine()))
    assert result["success"], f"recall team failed: {result}"
    print(f"    ✅ handle_recall(scope=team) 成功, count={len(result.get('memories', []))}")
    
    # recall all (should include team)
    result = json.loads(handle_recall({
        "query": "团队共享",
        "scope": "all",
        "top_k": 5
    }, cm=cm, engine=MockEngine()))
    assert result["success"], f"recall all failed: {result}"
    print(f"    ✅ handle_recall(scope=all) 成功, count={len(result.get('memories', []))}")
    
    # forget team
    result = json.loads(handle_forget({
        "memory_id": team_mem_id,
        "scope": "team"
    }, cm=cm))
    assert result["success"], f"forget team failed: {result}"
    print(f"    ✅ handle_forget(scope=team) 成功")
    
    # 清理测试数据
    print("\n[清理] 删除测试数据...")
    with cm.get_conn() as conn:
        conn.execute("DELETE FROM tasks WHERE project_dir=%s AND user_id=%s", (cm.project_dir, cm.user_id))
        conn.execute("DELETE FROM issues WHERE project_dir=%s AND user_id=%s", (cm.project_dir, cm.user_id))
        conn.execute("DELETE FROM memories WHERE project_dir=%s AND user_id=%s", (cm.project_dir, cm.user_id))
        conn.execute("DELETE FROM user_memories WHERE user_id=%s", (cm.user_id,))
        conn.execute("DELETE FROM team_memories WHERE project_dir=%s", (cm.project_dir,))
        conn.execute("DELETE FROM session_state WHERE project_dir=%s AND user_id=%s", (cm.project_dir, cm.user_id))
    print("    ✅ 测试数据已清理")
    
    cm.close()
    print("\n" + "=" * 60)
    print("✅ 所有 tools handler 测试通过")
    print("=" * 60)
    return True


if __name__ == "__main__":
    try:
        success = test_handlers()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
