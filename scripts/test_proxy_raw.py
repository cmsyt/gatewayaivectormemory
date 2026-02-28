"""用 raw socket 看 502 的实际响应体"""
import os, subprocess, sys, time, socket

PORT = 18097
BIND = "127.0.0.1"

proc = subprocess.Popen(
    [sys.executable, "-m", "uvicorn",
     "gatewayaivectormemory.proxy.app:create_app", "--factory",
     "--host", BIND, "--port", str(PORT), "--log-level", "debug"],
    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    env={
        **os.environ,
        "PYTHONPATH": ".",
        "GATEWAYAIVECTORMEMORY_PG_URL": "postgresql:///gatewayaivectormemory",
    },
)

time.sleep(8)

# raw HTTP request
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((BIND, PORT))
s.sendall(b"GET /memory/health HTTP/1.1\r\nHost: 127.0.0.1:18097\r\n\r\n")
time.sleep(2)
data = s.recv(4096)
print("Raw response:")
print(data.decode(errors="replace"))
s.close()

# also check uvicorn output
import fcntl
fcntl.fcntl(proc.stdout.fileno(), fcntl.F_SETFL, os.O_NONBLOCK)
try:
    out = proc.stdout.read()
    if out:
        print("\nServer output:")
        print(out.decode(errors="replace"))
except Exception:
    pass

proc.terminate()
proc.wait(5)
