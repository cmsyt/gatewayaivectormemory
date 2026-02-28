"""绕过 __main__.py，直接用 uvicorn CLI 启动 create_app"""
import json, os, subprocess, sys, time, urllib.request, urllib.error

PORT = 18096
BIND = "127.0.0.1"

# 直接用 uvicorn CLI 启动
proc = subprocess.Popen(
    [sys.executable, "-m", "uvicorn",
     "gatewayaivectormemory.proxy.app:create_app", "--factory",
     "--host", BIND, "--port", str(PORT), "--log-level", "info"],
    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    env={
        **os.environ,
        "PYTHONPATH": ".",
        "GATEWAYAIVECTORMEMORY_PG_URL": "postgresql:///gatewayaivectormemory",
    },
)

import fcntl
fcntl.fcntl(proc.stdout.fileno(), fcntl.F_SETFL, os.O_NONBLOCK)

started = False
for i in range(30):
    time.sleep(1)
    if proc.poll() is not None:
        out = proc.stdout.read().decode() if proc.stdout else ""
        print(f"Process exited: {proc.returncode}\n{out}")
        sys.exit(1)
    try:
        chunk = proc.stdout.read()
        if chunk:
            text = chunk.decode()
            sys.stdout.write(text)
            if "Application startup complete" in text:
                started = True
                break
    except Exception:
        pass
    print(f"[wait] {i+1}s...")

if not started:
    print("[wait] Startup not detected")
    proc.terminate()
    sys.exit(1)

print("[wait] Startup detected, testing health...")
time.sleep(1)
try:
    url = f"http://{BIND}:{PORT}/memory/health"
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=5) as resp:
        data = json.loads(resp.read())
        print(f"Health: {json.dumps(data)}")
        print("SUCCESS!")
except Exception as e:
    print(f"FAIL: {e}")

proc.terminate()
proc.wait(5)
