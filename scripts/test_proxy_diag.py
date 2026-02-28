"""诊断 memory-proxy 启动问题"""
import json, os, subprocess, sys, time, urllib.request, urllib.error, socket

PORT = 18092
BIND = "127.0.0.1"
PG_URL = os.environ.get("GATEWAYAIVECTORMEMORY_PG_URL", "postgresql:///gatewayaivectormemory")

def check_port(port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.connect(("127.0.0.1", port))
        s.close()
        return True
    except Exception:
        return False

def main():
    # 确认端口空闲
    if check_port(PORT):
        print(f"[diag] Port {PORT} already in use!")
        sys.exit(1)

    print(f"[diag] Starting memory-proxy on {BIND}:{PORT} ...")
    log_path = "/tmp/proxy_diag.log"
    log_file = open(log_path, "w")
    proc = subprocess.Popen(
        [sys.executable, "-m", "gatewayaivectormemory", "memory-proxy",
         "--port", str(PORT), "--bind", BIND, "--pg-url", PG_URL, "--workers", "1"],
        stdout=log_file, stderr=log_file,
        env={**os.environ, "PYTHONPATH": "."},
    )

    for i in range(30):
        time.sleep(1)
        rc = proc.poll()
        if rc is not None:
            log_file.close()
            with open(log_path) as f:
                print(f"[diag] Process exited with code {rc}")
                print(f.read())
            sys.exit(1)

        port_open = check_port(PORT)
        print(f"[diag] {i+1}s: pid={proc.pid} alive=True port_open={port_open}")

        if port_open:
            try:
                url = f"http://{BIND}:{PORT}/memory/health"
                req = urllib.request.Request(url)
                with urllib.request.urlopen(req, timeout=5) as resp:
                    data = json.loads(resp.read())
                    print(f"[diag] Health: {json.dumps(data)}")
                    print("[diag] SUCCESS!")
                    proc.terminate()
                    proc.wait(5)
                    log_file.close()
                    sys.exit(0)
            except Exception as e:
                print(f"[diag] HTTP error: {e}")

    print("[diag] Timeout - checking log:")
    log_file.close()
    with open(log_path) as f:
        print(f.read())
    proc.terminate()
    proc.wait(5)
    sys.exit(1)

if __name__ == "__main__":
    main()
