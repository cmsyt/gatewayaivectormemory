"""直接在进程内启动 uvicorn 并测试"""
import os, sys, threading, time, json, urllib.request, urllib.error, socket

os.environ["GATEWAYAIVECTORMEMORY_PG_URL"] = os.environ.get(
    "GATEWAYAIVECTORMEMORY_PG_URL", "postgresql:///gatewayaivectormemory"
)

PORT = 18093
BIND = "127.0.0.1"

def run_server():
    import uvicorn
    from gatewayaivectormemory.proxy.app import create_app
    app = create_app()
    uvicorn.run(app, host=BIND, port=PORT, log_level="info")

t = threading.Thread(target=run_server, daemon=True)
t.start()

for i in range(30):
    time.sleep(1)
    try:
        url = f"http://{BIND}:{PORT}/memory/health"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
            print(f"[test] Health: {json.dumps(data)}")
            print("[test] SUCCESS!")
            sys.exit(0)
    except urllib.error.HTTPError as e:
        print(f"[test] {i+1}s: HTTP {e.code}")
    except Exception as e:
        print(f"[test] {i+1}s: {type(e).__name__}: {e}")

print("[test] TIMEOUT")
sys.exit(1)
