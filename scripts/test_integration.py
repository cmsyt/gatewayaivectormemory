#!/usr/bin/env python3
"""第 8 组集成测试：端到端 REST API + 用户隔离 + team scope + 认证"""
import http.client
import json
import os
import signal
import subprocess
import sys
import time

PG_URL = os.environ.get("GATEWAYAIVECTORMEMORY_PG_URL", "postgresql:///gatewayaivectormemory")
EMBED_PORT = 18900
PROXY_PORT = 18080
TOKEN = "test-integration-token-2026"
PROJECT_DIR = "/tmp/test-integration-project"
USER_A = "user-alice"
USER_B = "user-bob"

procs = []

def cleanup():
    for p in procs:
        try:
            p.send_signal(signal.SIGTERM)
            p.wait(timeout=3)
        except Exception:
            p.kill()

def api(method, path, body=None, headers=None, port=PROXY_PORT):
    """发送 HTTP 请求，每次新建连接避免 502 复用问题"""
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    hdrs = headers or {}
    if body is not None:
        payload = json.dumps(body).encode()
        hdrs["Content-Type"] = "application/json"
    else:
        payload = None
    conn.request(method, path, body=payload, headers=hdrs)
    resp = conn.getresponse()
    data = resp.read().decode()
    conn.close()
    try:
        return resp.status, json.loads(data)
    except Exception:
        return resp.status, data

def auth_headers(user_id, project_dir=PROJECT_DIR):
    return {
        "Authorization": f"Bearer {TOKEN}",
        "X-User-Id": user_id,
        "X-Project-Dir": project_dir,
    }

def wait_for_health(port, path="/memory/health", timeout=15):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            conn = http.client.HTTPConnection("127.0.0.1", port, timeout=3)
            conn.request("GET", path)
            resp = conn.getresponse()
            resp.read()
            conn.close()
            if resp.status == 200:
                return True
        except Exception:
            pass
        time.sleep(0.5)
    return False

def assert_ok(label, status, body, expected_status=200):
    success = body.get("success", False) if isinstance(body, dict) else False
    if status != expected_status or (expected_status == 200 and not success):
        print(f"  FAIL {label}: status={status} body={json.dumps(body, ensure_ascii=False)[:200]}")
        return False
    print(f"  PASS {label}")
    return True

def assert_status(label, status, expected):
    if status != expected:
        print(f"  FAIL {label}: expected {expected}, got {status}")
        return False
    print(f"  PASS {label}")
    return True


def main():
    passed = 0
    failed = 0

    def check(ok):
        nonlocal passed, failed
        if ok:
            passed += 1
        else:
            failed += 1

    python = os.path.join(os.path.dirname(__file__), "..", ".venv", "bin", "python")
    python = os.path.abspath(python)
    project_root = os.path.join(os.path.dirname(__file__), "..")
    env = {**os.environ, "PYTHONPATH": project_root, "GATEWAYAIVECTORMEMORY_PG_URL": PG_URL}

    # --- 启动 embed-server ---
    print("[1] Starting embed-server...")
    embed_proc = subprocess.Popen(
        [python, "-m", "gatewayaivectormemory", "embed-server", "--port", str(EMBED_PORT)],
        env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    procs.append(embed_proc)
    if not wait_for_health(EMBED_PORT, "/health"):
        print("FATAL: embed-server failed to start")
        cleanup()
        sys.exit(1)
    print("  embed-server ready")

    # --- 启动 memory-proxy (带 token 认证) ---
    print("[2] Starting memory-proxy with token auth...")
    proxy_proc = subprocess.Popen(
        [python, "-m", "gatewayaivectormemory", "memory-proxy",
         "--port", str(PROXY_PORT), "--bind", "127.0.0.1",
         "--pg-url", PG_URL,
         "--embed-url", f"http://127.0.0.1:{EMBED_PORT}",
         "--token", TOKEN, "--workers", "1"],
        env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    procs.append(proxy_proc)
    if not wait_for_health(PROXY_PORT):
        print("FATAL: memory-proxy failed to start")
        err = proxy_proc.stderr.read().decode() if proxy_proc.stderr else ""
        print(f"  stderr: {err[:500]}")
        cleanup()
        sys.exit(1)
    print("  memory-proxy ready")

    # ========================================
    # 8.4 认证测试：无 token 请求返回 401
    # ========================================
    print("\n[8.4] Auth test: no token -> 401")
    s, b = api("POST", "/memory/status", {}, {"X-User-Id": USER_A, "X-Project-Dir": PROJECT_DIR})
    check(assert_status("no-token-401", s, 401))

    s, b = api("POST", "/memory/recall", {"query": "test"}, {"X-User-Id": USER_A, "X-Project-Dir": PROJECT_DIR})
    check(assert_status("no-token-recall-401", s, 401))

    # ========================================
    # 8.1 端到端测试：调用全部 REST API
    # ========================================
    print("\n[8.1] E2E test: all REST APIs")
    h = auth_headers(USER_A)

    # status (read)
    s, b = api("POST", "/memory/status", {}, h)
    check(assert_ok("status-read", s, b))

    # status (write)
    s, b = api("POST", "/memory/status", {"state": {"current_task": "integration test"}}, h)
    check(assert_ok("status-write", s, b))

    # remember (project scope)
    s, b = api("POST", "/memory/remember", {
        "content": "Integration test memory from Alice",
        "tags": ["test", "integration"],
        "scope": "project",
    }, h)
    check(assert_ok("remember-project", s, b))
    alice_mem_id = b.get("data", {}).get("id", "") if isinstance(b, dict) else ""

    # recall
    s, b = api("POST", "/memory/recall", {"query": "integration test", "scope": "project", "top_k": 5}, h)
    check(assert_ok("recall", s, b))
    recall_memories = b.get("data", {}).get("memories", []) if isinstance(b, dict) else []
    found_alice = any("Integration test memory from Alice" in m.get("content", "") for m in recall_memories)
    check(assert_status("recall-found-alice", 200 if found_alice else 404, 200))

    # track create
    s, b = api("POST", "/memory/track", {
        "action": "create",
        "title": "Integration test issue",
        "content": "Testing track create from integration test",
    }, h)
    check(assert_ok("track-create", s, b))

    # track list
    s, b = api("POST", "/memory/track", {"action": "list"}, h)
    check(assert_ok("track-list", s, b))

    # task batch_create
    s, b = api("POST", "/memory/task", {
        "action": "batch_create",
        "feature_id": "test-integration",
        "tasks": [{"title": "Test task 1"}, {"title": "Test task 2"}],
    }, h)
    check(assert_ok("task-batch-create", s, b))

    # task list
    s, b = api("POST", "/memory/task", {"action": "list", "feature_id": "test-integration"}, h)
    check(assert_ok("task-list", s, b))

    # auto_save
    s, b = api("POST", "/memory/auto_save", {"preferences": ["test preference"]}, h)
    check(assert_ok("auto-save", s, b))

    # forget
    if alice_mem_id:
        s, b = api("POST", "/memory/forget", {"memory_id": alice_mem_id}, h)
        check(assert_ok("forget", s, b))
    else:
        print("  SKIP forget (no memory_id)")

    # ========================================
    # 8.2 用户隔离测试
    # ========================================
    print("\n[8.2] User isolation test")
    hA = auth_headers(USER_A)
    hB = auth_headers(USER_B)

    # Alice remember
    s, b = api("POST", "/memory/remember", {
        "content": "Alice secret data for isolation test",
        "tags": ["isolation", "alice"],
        "scope": "project",
    }, hA)
    check(assert_ok("alice-remember", s, b))

    # Bob recall should NOT find Alice's data
    s, b = api("POST", "/memory/recall", {"query": "Alice secret data", "scope": "project", "top_k": 10}, hB)
    check(assert_ok("bob-recall", s, b))
    bob_memories = b.get("data", {}).get("memories", []) if isinstance(b, dict) else []
    alice_leaked = any("Alice secret data" in m.get("content", "") for m in bob_memories)
    check(assert_status("bob-no-alice-data", 200 if not alice_leaked else 403, 200))

    # Alice recall should find her own data
    s, b = api("POST", "/memory/recall", {"query": "Alice secret data", "scope": "project", "top_k": 10}, hA)
    check(assert_ok("alice-recall-own", s, b))
    alice_memories = b.get("data", {}).get("memories", []) if isinstance(b, dict) else []
    alice_found = any("Alice secret data" in m.get("content", "") for m in alice_memories)
    check(assert_status("alice-finds-own", 200 if alice_found else 404, 200))

    # ========================================
    # 8.3 Team scope 测试
    # ========================================
    print("\n[8.3] Team scope test")

    # Alice remember with team scope
    s, b = api("POST", "/memory/remember", {
        "content": "Team shared knowledge from Alice",
        "tags": ["team", "shared"],
        "scope": "team",
    }, hA)
    check(assert_ok("alice-team-remember", s, b))

    # Bob recall with team scope should find Alice's team memory
    time.sleep(0.5)  # small delay for consistency
    s, b = api("POST", "/memory/recall", {"query": "Team shared knowledge", "scope": "team", "top_k": 10}, hB)
    check(assert_ok("bob-team-recall", s, b))
    bob_team = b.get("data", {}).get("memories", []) if isinstance(b, dict) else []
    team_found = any("Team shared knowledge" in m.get("content", "") for m in bob_team)
    check(assert_status("bob-finds-team-data", 200 if team_found else 404, 200))

    # ========================================
    # Summary
    # ========================================
    print(f"\n{'='*40}")
    print(f"Results: {passed} passed, {failed} failed")
    print(f"{'='*40}")

    cleanup()
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        cleanup()
    except Exception as e:
        print(f"FATAL: {e}")
        import traceback
        traceback.print_exc()
        cleanup()
        sys.exit(1)
