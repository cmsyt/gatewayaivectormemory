"""简单测试 memory-proxy 启动"""
import subprocess
import sys
import os

proc = subprocess.Popen(
    [sys.executable, "-m", "gatewayaivectormemory", "memory-proxy",
     "--port", "18080", "--bind", "127.0.0.1",
     "--pg-url", "postgresql:///gatewayaivectormemory", "--workers", "1"],
    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    env={**os.environ, "PYTHONPATH": "."},
)
try:
    out, err = proc.communicate(timeout=10)
    print(f"Exit code: {proc.returncode}")
    if out: print(f"STDOUT:\n{out.decode()}")
    if err: print(f"STDERR:\n{err.decode()}")
except subprocess.TimeoutExpired:
    print("Process still running after 10s (good sign)")
    proc.terminate()
    out, err = proc.communicate(timeout=5)
    if out: print(f"STDOUT:\n{out.decode()}")
    if err: print(f"STDERR:\n{err.decode()}")
