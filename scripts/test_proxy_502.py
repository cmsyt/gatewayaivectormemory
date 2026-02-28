"""诊断 502 错误的具体内容"""
import os, sys, threading, time, json, http.client

os.environ["GATEWAYAIVECTORMEMORY_PG_URL"] = os.environ.get(
    "GATEWAYAIVECTORMEMORY_PG_URL", "postgresql:///gatewayaivectormemory"
)

PORT = 18094
BIND = "127.0.0.1"

def run_server():
    import uvicorn
    from gatewayaivectormemory.proxy.app import create_app
    app = create_app()
    uvicorn.run(app, host=BIND, port=PORT, log_level="debug")

t = threading.Thread(target=run_server, daemon=True)
t.start()

time.sleep(8)  # wait for startup

conn = http.client.HTTPConnection(BIND, PORT, timeout=10)
conn.request("GET", "/memory/health")
resp = conn.getresponse()
print(f"Status: {resp.status} {resp.reason}")
print(f"Headers: {dict(resp.getheaders())}")
body = resp.read()
print(f"Body: {body.decode()}")
conn.close()
