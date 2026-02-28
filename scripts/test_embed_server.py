"""测试 embed-server HTTP 接口 (用 curl 避免代理干扰)"""
import json
import subprocess

BASE = "http://127.0.0.1:8901"

def curl_get(path):
    r = subprocess.run(["curl", "-s", f"{BASE}{path}"], capture_output=True, text=True, timeout=15)
    return json.loads(r.stdout)

def curl_post(path, data):
    r = subprocess.run(
        ["curl", "-s", "-X", "POST", f"{BASE}{path}",
         "-H", "Content-Type: application/json",
         "-d", json.dumps(data)],
        capture_output=True, text=True, timeout=15
    )
    return json.loads(r.stdout)

def curl_post_status(path, data):
    r = subprocess.run(
        ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}",
         "-X", "POST", f"{BASE}{path}",
         "-H", "Content-Type: application/json",
         "-d", json.dumps(data)],
        capture_output=True, text=True, timeout=15
    )
    return int(r.stdout.strip())

# 1. GET /health
print("=== GET /health ===")
r = curl_get("/health")
print(r)
assert r["status"] == "ok"
assert r["dimension"] == 384
print("PASS\n")

# 2. POST /encode
print("=== POST /encode ===")
r = curl_post("/encode", {"text": "hello world"})
print(f"dimension={r['dimension']}, vector_len={len(r['vector'])}")
assert r["dimension"] == 384
assert len(r["vector"]) == 384
assert isinstance(r["vector"][0], float)
print("PASS\n")

# 3. POST /encode - missing text
print("=== POST /encode (missing text) ===")
code = curl_post_status("/encode", {"text": ""})
print(f"HTTP status: {code}")
assert code == 400
print("PASS\n")

# 4. POST /encode_batch
print("=== POST /encode_batch ===")
r = curl_post("/encode_batch", {"texts": ["hello", "world", "test"]})
print(f"dimension={r['dimension']}, num_vectors={len(r['vectors'])}")
assert len(r["vectors"]) == 3
assert all(len(v) == 384 for v in r["vectors"])
print("PASS\n")

# 5. POST /encode_batch - missing texts
print("=== POST /encode_batch (missing texts) ===")
code = curl_post_status("/encode_batch", {"texts": []})
print(f"HTTP status: {code}")
assert code == 400
print("PASS\n")

print("All embed-server tests passed!")
