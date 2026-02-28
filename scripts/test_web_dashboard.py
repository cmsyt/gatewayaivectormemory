"""验证 Web 看板启动和基本功能"""
import subprocess, sys, time, http.client, json, signal, os

PG_URL = "postgresql:///gatewayaivectormemory"
PORT = 9081
BIND = "127.0.0.1"
TOKEN = "test-token-abc123"

def req(method, path, expected_status=200):
    conn = http.client.HTTPConnection(BIND, PORT, timeout=5)
    headers = {"Authorization": f"Bearer {TOKEN}"}
    conn.request(method, path, headers=headers)
    resp = conn.getresponse()
    body = resp.read().decode()
    conn.close()
    return resp.status, body

def req_no_auth(method, path):
    conn = http.client.HTTPConnection(BIND, PORT, timeout=5)
    conn.request(method, path)
    resp = conn.getresponse()
    body = resp.read().decode()
    conn.close()
    return resp.status, body

def main():
    env = os.environ.copy()
    env["PYTHONPATH"] = "."
    env["GATEWAYAIVECTORMEMORY_PG_URL"] = PG_URL

    print("[1] 启动 web 看板...")
    proc = subprocess.Popen(
        [".venv/bin/python", "-m", "gatewayaivectormemory", "web",
         "--pg-url", PG_URL, "--port", str(PORT), "--bind", BIND,
         "--token", TOKEN, "--quiet"],
        env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )

    # 等待启动
    ok = False
    for i in range(30):
        time.sleep(0.5)
        try:
            status, body = req_no_auth("GET", "/api/health")
            if status == 200:
                data = json.loads(body)
                if data.get("status") in ("ok", "degraded"):
                    ok = True
                    break
        except Exception:
            pass
    
    if not ok:
        print("FAIL: 看板未能在 15 秒内启动")
        proc.terminate()
        proc.wait()
        stderr = proc.stderr.read().decode()
        print(f"stderr: {stderr}")
        sys.exit(1)

    print("[2] health 检查通过")

    # 测试认证：无 token 访问 API 应返回 401
    status, _ = req_no_auth("GET", "/api/projects")
    assert status == 401, f"无 token 应返回 401, 实际 {status}"
    print("[3] 认证拦截正常 (401)")

    # 测试认证：有 token 访问 API
    status, body = req("GET", "/api/projects")
    assert status == 200, f"有 token 应返回 200, 实际 {status}"
    print(f"[4] 项目列表正常 (200), body length={len(body)}")

    # 测试静态文件
    status, body = req_no_auth("GET", "/")
    assert status == 200, f"首页应返回 200, 实际 {status}"
    assert "<!DOCTYPE html>" in body or "<html" in body, "首页应返回 HTML"
    print("[5] 静态文件服务正常")

    # 测试 health 详情
    status, body = req_no_auth("GET", "/api/health")
    data = json.loads(body)
    assert data.get("postgresql") is True, f"PostgreSQL 应连接正常, 实际 {data}"
    print(f"[6] PostgreSQL 连接正常: {data}")

    print("\n✅ 全部测试通过")
    proc.terminate()
    proc.wait()

if __name__ == "__main__":
    main()
