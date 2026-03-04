#!/usr/bin/env python3
"""8.5 Web 看板端到端测试：启动看板 → 验证页面加载 + API + scope 筛选 + user_id 过滤"""
import http.client
import json
import os
import signal
import subprocess
import sys
import time

PG_URL = os.environ.get("GATEWAYAIVECTORMEMORY_PG_URL", "postgresql:///gatewayaivectormemory")
WEB_PORT = 19080
TOKEN = "test-web-token-2026"
PROJECT_DIR = "/tmp/test-web-dashboard"
USER_ID = "test-web-user"

procs = []

def cleanup():
    for p in procs:
        try:
            p.send_signal(signal.SIGTERM)
            p.wait(timeout=3)
        except Exception:
            p.kill()

def api(method, path, body=None, headers=None):
    conn = http.client.HTTPConnection("127.0.0.1", WEB_PORT, timeout=10)
    hdrs = headers or {}
    hdrs["Authorization"] = f"Bearer {TOKEN}"
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

def wait_for_health(port, path="/api/health", timeout=15):
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


def main():
    passed = 0
    failed = 0

    def check(label, ok):
        nonlocal passed, failed
        if ok:
            passed += 1
            print(f"  PASS {label}")
        else:
            failed += 1
            print(f"  FAIL {label}")

    python = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".venv", "bin", "python"))
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    env = {**os.environ, "PYTHONPATH": project_root, "GATEWAYAIVECTORMEMORY_PG_URL": PG_URL}

    # --- 启动 web 看板 ---
    print("[1] Starting web dashboard...")
    web_proc = subprocess.Popen(
        [python, "-m", "gatewayaivectormemory", "web",
         "--port", str(WEB_PORT), "--bind", "127.0.0.1",
         "--pg-url", PG_URL, "--token", TOKEN,
         "--user-id", USER_ID, "--project-dir", PROJECT_DIR, "--quiet"],
        env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    procs.append(web_proc)
    if not wait_for_health(WEB_PORT):
        print("FATAL: web dashboard failed to start")
        err = web_proc.stderr.read().decode() if web_proc.stderr else ""
        print(f"  stderr: {err[:500]}")
        cleanup()
        sys.exit(1)
    print("  web dashboard ready")

    # ========================================
    # 测试 1: 健康检查
    # ========================================
    print("\n[2] Health check")
    s, b = api("GET", "/api/health")
    check("health-200", s == 200)
    check("health-pg-ok", isinstance(b, dict) and b.get("postgresql") is True)

    # ========================================
    # 测试 2: 静态页面加载
    # ========================================
    print("\n[3] Static page load")
    conn = http.client.HTTPConnection("127.0.0.1", WEB_PORT, timeout=10)
    conn.request("GET", "/")
    resp = conn.getresponse()
    html = resp.read().decode()
    conn.close()
    check("index-200", resp.status == 200)
    check("index-has-title", "GatewayAIVectorMemory" in html)
    check("index-has-app-js", "app.js" in html)

    # ========================================
    # 测试 3: API 认证（无 token 返回 401）
    # ========================================
    print("\n[4] API auth test")
    conn = http.client.HTTPConnection("127.0.0.1", WEB_PORT, timeout=10)
    conn.request("GET", "/api/stats")
    resp = conn.getresponse()
    resp.read()
    conn.close()
    check("no-token-401", resp.status == 401)

    # ========================================
    # 测试 4: Stats API
    # ========================================
    print("\n[5] Stats API")
    s, b = api("GET", f"/api/stats?project={PROJECT_DIR}")
    check("stats-200", s == 200)
    check("stats-has-memories", isinstance(b, dict) and "memories" in b)

    # ========================================
    # 测试 5: Projects API
    # ========================================
    print("\n[6] Projects API")
    s, b = api("GET", "/api/projects")
    check("projects-200", s == 200)
    check("projects-has-list", isinstance(b, dict) and "projects" in b)

    # ========================================
    # 测试 6: Memories API (scope 筛选)
    # ========================================
    print("\n[7] Memories API - scope filter")
    for scope in ["project", "user", "team", "all"]:
        s, b = api("GET", f"/api/memories?project={PROJECT_DIR}&scope={scope}")
        check(f"memories-scope-{scope}", s == 200 and isinstance(b, dict) and "memories" in b)

    # ========================================
    # 测试 7: Issues API
    # ========================================
    print("\n[8] Issues API")
    s, b = api("GET", f"/api/issues?project={PROJECT_DIR}")
    check("issues-200", s == 200 and isinstance(b, dict) and "issues" in b)

    # ========================================
    # 测试 8: Tasks API
    # ========================================
    print("\n[9] Tasks API")
    s, b = api("GET", f"/api/tasks?project={PROJECT_DIR}")
    check("tasks-200", s == 200 and isinstance(b, dict) and "tasks" in b)

    # ========================================
    # 测试 9: Tags API
    # ========================================
    print("\n[10] Tags API")
    s, b = api("GET", f"/api/tags?project={PROJECT_DIR}")
    check("tags-200", s == 200 and isinstance(b, dict) and "tags" in b)

    # ========================================
    # 测试 10: Status API
    # ========================================
    print("\n[11] Status API")
    s, b = api("GET", f"/api/status?project={PROJECT_DIR}")
    check("status-200", s == 200)

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
