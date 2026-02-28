"""Memory Proxy 启动验证脚本：启动服务 → 调用 /memory/health → 验证响应"""
import json
import os
import subprocess
import sys
import time
import http.client

PG_URL = os.environ.get("GATEWAYAIVECTORMEMORY_PG_URL", "postgresql:///gatewayaivectormemory")
PORT = 18090
BIND = "127.0.0.1"
TIMEOUT = 30


def main():
    print(f"[test] Starting memory-proxy on {BIND}:{PORT} ...")
    log_file = open("/tmp/memory_proxy_test.log", "w")
    proc = subprocess.Popen(
        [sys.executable, "-m", "gatewayaivectormemory", "memory-proxy",
         "--port", str(PORT), "--bind", BIND, "--pg-url", PG_URL, "--workers", "1"],
        stdout=log_file, stderr=log_file,
        env={**os.environ, "PYTHONPATH": "."},
    )

    health_url = f"http://{BIND}:{PORT}/memory/health"
    started = False
    for i in range(TIMEOUT):
        time.sleep(1)
        if proc.poll() is not None:
            log_file.close()
            with open("/tmp/memory_proxy_test.log") as f:
                print(f"[test] FAIL: process exited with code {proc.returncode}")
                print(f.read())
            sys.exit(1)
        try:
            conn = http.client.HTTPConnection(BIND, PORT, timeout=3)
            conn.request("GET", "/memory/health")
            resp = conn.getresponse()
            if resp.status == 200:
                data = json.loads(resp.read())
                conn.close()
                print(f"[test] Health response: {json.dumps(data)}")
                if data.get("postgresql") is True:
                    started = True
                    break
            else:
                conn.close()
                print(f"[test] Waiting... ({i+1}s, HTTP {resp.status})")
        except Exception:
            print(f"[test] Waiting... ({i+1}s)")

    if not started:
        print("[test] FAIL: service did not start within timeout")
        proc.terminate()
        proc.wait(5)
        log_file.close()
        with open("/tmp/memory_proxy_test.log") as f:
            print(f.read())
        sys.exit(1)

    # 测试缺少 header 返回 400
    print("[test] Testing missing headers -> 400 ...")
    try:
        conn = http.client.HTTPConnection(BIND, PORT, timeout=5)
        conn.request("POST", "/memory/status", body=b"{}", headers={"Content-Type": "application/json"})
        resp = conn.getresponse()
        resp.read()
        conn.close()
        if resp.status == 400:
            print("[test] OK: got 400 as expected")
        else:
            print(f"[test] FAIL: expected 400 but got {resp.status}")
            _cleanup(proc, log_file)
            sys.exit(1)
    except Exception as e:
        print(f"[test] FAIL: {e}")
        _cleanup(proc, log_file)
        sys.exit(1)

    # 测试带 header 的 status 调用
    print("[test] Testing POST /memory/status with headers ...")
    try:
        conn = http.client.HTTPConnection(BIND, PORT, timeout=10)
        conn.request("POST", "/memory/status", body=b"{}",
                      headers={"Content-Type": "application/json",
                               "X-User-Id": "test-user",
                               "X-Project-Dir": "/tmp/test-project"})
        resp = conn.getresponse()
        body = resp.read()
        conn.close()
        if resp.status == 200:
            data = json.loads(body)
            print(f"[test] Status response: success={data.get('success')}")
            if data.get("success") is True:
                print("[test] OK: status call succeeded")
            else:
                print(f"[test] FAIL: {data}")
                _cleanup(proc, log_file)
                sys.exit(1)
        else:
            print(f"[test] FAIL: HTTP {resp.status} {body.decode()}")
            _cleanup(proc, log_file)
            sys.exit(1)
    except Exception as e:
        print(f"[test] FAIL: {e}")
        _cleanup(proc, log_file)
        sys.exit(1)

    print("[test] All tests passed!")
    _cleanup(proc, log_file)


def _cleanup(proc, log_file):
    proc.terminate()
    try:
        proc.wait(5)
    except subprocess.TimeoutExpired:
        proc.kill()
    log_file.close()


if __name__ == "__main__":
    main()
