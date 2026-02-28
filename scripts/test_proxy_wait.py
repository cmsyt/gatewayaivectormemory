"""subprocess 模式，等更久再请求"""
import json, os, subprocess, sys, time, urllib.request, urllib.error, socket

PORT = 18095
BIND = "127.0.0.1"
PG_URL = os.environ.get("GATEWAYAIVECTORMEMORY_PG_URL", "postgresql:///gatewayaivectormemory")

proc = subprocess.Popen(
    [sys.executable, "-m", "gatewayaivectormemory", "memory-proxy",
     "--port", str(PORT), "--bind", BIND, "--pg-url", PG_URL, "--workers", "1"],
    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    env={**os.environ, "PYTHONPATH": "."},
)

# 等 startup complete 出现在输出中
import select, fcntl
fcntl.fcntl(proc.stdout.fileno(), fcntl.F_SETFL, os.O_NONBLOCK)

started = False
for i in range(30):
    time.sleep(1)
    if proc.poll() is not None:
        print(f"Process exited: {proc.returncode}")
        print(proc.stdout.read().decode())
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
        print(f"[wait] Health: {json.dumps(data)}")
        print("[wait] SUCCESS!")
except Exception as e:
    print(f"[wait] FAIL: {e}")

proc.terminate()
proc.wait(5)
