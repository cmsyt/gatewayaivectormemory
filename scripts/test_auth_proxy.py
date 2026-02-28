"""认证与鉴权测试脚本：测试 auth middleware + 角色权限控制"""
import json
import os
import subprocess
import sys
import time
import http.client
import jwt

PG_URL = os.environ.get("GATEWAYAIVECTORMEMORY_PG_URL", "postgresql:///gatewayaivectormemory")
PORT = 18091
BIND = "127.0.0.1"
TIMEOUT = 30
TOKEN = "test-admin-token-12345"
JWT_SECRET = None  # 单独测试 JWT 时用
LOG_FILE = "/tmp/auth_proxy_test.log"


def req(method, path, body=None, headers=None, port=PORT):
    conn = http.client.HTTPConnection(BIND, port, timeout=10)
    hdrs = {"Content-Type": "application/json"}
    if headers:
        hdrs.update(headers)
    conn.request(method, path, body=json.dumps(body).encode() if body else None, headers=hdrs)
    resp = conn.getresponse()
    data = resp.read()
    conn.close()
    return resp.status, data


def start_proxy(extra_args=None):
    args = [
        sys.executable, "-m", "gatewayaivectormemory", "memory-proxy",
        "--port", str(PORT), "--bind", BIND, "--pg-url", PG_URL, "--workers", "1",
    ]
    if extra_args:
        args.extend(extra_args)
    log = open(LOG_FILE, "w")
    proc = subprocess.Popen(args, stdout=log, stderr=log, env={**os.environ, "PYTHONPATH": "."})
    # wait for startup
    for i in range(TIMEOUT):
        time.sleep(1)
        if proc.poll() is not None:
            log.close()
            with open(LOG_FILE) as f:
                print(f"[test] FAIL: process exited with code {proc.returncode}")
                print(f.read())
            sys.exit(1)
        try:
            status, _ = req("GET", "/memory/health", port=PORT)
            if status == 200:
                print(f"[test] Proxy started ({i+1}s)")
                return proc, log
        except Exception:
            pass
    print("[test] FAIL: startup timeout")
    proc.terminate()
    log.close()
    sys.exit(1)


def cleanup(proc, log):
    proc.terminate()
    try:
        proc.wait(5)
    except subprocess.TimeoutExpired:
        proc.kill()
    log.close()


def test_no_auth_localhost():
    """测试1：无认证模式，localhost 可访问"""
    print("\n=== Test 1: No auth, localhost access ===")
    proc, log = start_proxy()
    try:
        # health 不需要认证
        status, body = req("GET", "/memory/health")
        assert status == 200, f"health expected 200, got {status}"
        print("[test] health OK")

        # localhost 访问 status 应该成功（admin 角色）
        status, body = req("POST", "/memory/status", body={},
                           headers={"X-User-Id": "test-user", "X-Project-Dir": "/tmp/test"})
        assert status == 200, f"status expected 200, got {status}: {body.decode()}"
        print("[test] localhost status OK")

        print("[test] Test 1 PASSED")
    finally:
        cleanup(proc, log)


def test_token_auth():
    """测试2：token 认证模式"""
    print("\n=== Test 2: Token auth ===")
    proc, log = start_proxy(["--token", TOKEN])
    try:
        # 无 token 访问应返回 401
        status, body = req("POST", "/memory/status", body={},
                           headers={"X-User-Id": "test-user", "X-Project-Dir": "/tmp/test"})
        assert status == 401, f"expected 401 without token, got {status}"
        print("[test] 401 without token OK")

        # 错误 token 应返回 401
        status, body = req("POST", "/memory/status", body={},
                           headers={"X-User-Id": "test-user", "X-Project-Dir": "/tmp/test",
                                    "Authorization": "Bearer wrong-token"})
        assert status == 401, f"expected 401 with wrong token, got {status}"
        print("[test] 401 with wrong token OK")

        # 正确 token 应返回 200（admin 角色）
        status, body = req("POST", "/memory/status", body={},
                           headers={"X-User-Id": "test-user", "X-Project-Dir": "/tmp/test",
                                    "Authorization": f"Bearer {TOKEN}"})
        assert status == 200, f"expected 200 with correct token, got {status}: {body.decode()}"
        print("[test] 200 with correct token OK (admin)")

        # health 不需要 token
        status, _ = req("GET", "/memory/health")
        assert status == 200, f"health expected 200, got {status}"
        print("[test] health without token OK")

        print("[test] Test 2 PASSED")
    finally:
        cleanup(proc, log)


def test_jwt_auth():
    """测试3：JWT 认证模式"""
    print("\n=== Test 3: JWT auth ===")
    secret = "test-jwt-secret-xyz"
    proc, log = start_proxy(["--jwt-secret", secret])
    try:
        # 无 token 应返回 401
        status, _ = req("POST", "/memory/status", body={},
                         headers={"X-User-Id": "u1", "X-Project-Dir": "/tmp/test"})
        assert status == 401, f"expected 401, got {status}"
        print("[test] 401 without JWT OK")

        # 有效 JWT (admin)
        admin_token = jwt.encode({"user_id": "admin-1", "role": "admin"}, secret, algorithm="HS256")
        status, body = req("POST", "/memory/status", body={},
                           headers={"X-User-Id": "any-user", "X-Project-Dir": "/tmp/test",
                                    "Authorization": f"Bearer {admin_token}"})
        assert status == 200, f"expected 200 with admin JWT, got {status}: {body.decode()}"
        print("[test] 200 with admin JWT OK")

        # 有效 JWT (user) - user_id 应被强制为 JWT 中的值
        user_token = jwt.encode({"user_id": "user-alice", "role": "user"}, secret, algorithm="HS256")
        status, body = req("POST", "/memory/status", body={},
                           headers={"X-User-Id": "should-be-ignored", "X-Project-Dir": "/tmp/test",
                                    "Authorization": f"Bearer {user_token}"})
        assert status == 200, f"expected 200 with user JWT, got {status}: {body.decode()}"
        print("[test] 200 with user JWT OK")

        # 无效 JWT
        bad_token = jwt.encode({"user_id": "x"}, "wrong-secret", algorithm="HS256")
        status, _ = req("POST", "/memory/status", body={},
                         headers={"X-User-Id": "u1", "X-Project-Dir": "/tmp/test",
                                  "Authorization": f"Bearer {bad_token}"})
        assert status == 401, f"expected 401 with bad JWT, got {status}"
        print("[test] 401 with invalid JWT OK")

        print("[test] Test 3 PASSED")
    finally:
        cleanup(proc, log)


def main():
    print("[test] Auth proxy test suite")
    test_no_auth_localhost()
    test_token_auth()
    test_jwt_auth()
    print("\n[test] All auth tests PASSED!")


if __name__ == "__main__":
    main()
