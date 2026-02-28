"""embed-server 全接口自测脚本"""
import json
import os
import urllib.request
import sys

os.environ["no_proxy"] = "*"
BASE = "http://127.0.0.1:8900"
errors = []

def req(method, path, data=None):
    url = f"{BASE}{path}"
    body = json.dumps(data).encode() if data else None
    r = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"} if body else {}, method=method)
    with urllib.request.urlopen(r, timeout=15) as resp:
        return json.loads(resp.read())

# 1. GET /health
print("=== Test 1: GET /health ===")
try:
    res = req("GET", "/health")
    assert res["status"] == "ok", f"Expected ok, got {res['status']}"
    assert res["model"] == "intfloat/multilingual-e5-small"
    assert res["dimension"] == 384
    print(f"  PASS: {res}")
except Exception as e:
    errors.append(f"health: {e}")
    print(f"  FAIL: {e}")

# 2. POST /encode
print("=== Test 2: POST /encode ===")
try:
    res = req("POST", "/encode", {"text": "hello world"})
    vec = res["vector"]
    assert isinstance(vec, list) and len(vec) == 384, f"Expected 384-dim vector, got {len(vec)}"
    assert res["dimension"] == 384
    print(f"  PASS: vector length={len(vec)}, dimension={res['dimension']}")
except Exception as e:
    errors.append(f"encode: {e}")
    print(f"  FAIL: {e}")

# 3. POST /encode - missing text
print("=== Test 3: POST /encode (missing text) ===")
try:
    r = urllib.request.Request(f"{BASE}/encode", data=json.dumps({}).encode(), headers={"Content-Type": "application/json"})
    urllib.request.urlopen(r, timeout=10)
    errors.append("encode_missing: expected 400")
    print("  FAIL: expected 400")
except urllib.error.HTTPError as e:
    if e.code == 400:
        print(f"  PASS: got 400 as expected")
    else:
        errors.append(f"encode_missing: unexpected {e.code}")
        print(f"  FAIL: unexpected {e.code}")

# 4. POST /encode_batch
print("=== Test 4: POST /encode_batch ===")
try:
    res = req("POST", "/encode_batch", {"texts": ["hello", "world", "test"]})
    vecs = res["vectors"]
    assert len(vecs) == 3, f"Expected 3 vectors, got {len(vecs)}"
    assert all(len(v) == 384 for v in vecs), "Not all vectors are 384-dim"
    assert res["dimension"] == 384
    print(f"  PASS: {len(vecs)} vectors, each 384-dim")
except Exception as e:
    errors.append(f"encode_batch: {e}")
    print(f"  FAIL: {e}")

# 5. POST /encode_batch - missing texts
print("=== Test 5: POST /encode_batch (missing texts) ===")
try:
    r = urllib.request.Request(f"{BASE}/encode_batch", data=json.dumps({}).encode(), headers={"Content-Type": "application/json"})
    urllib.request.urlopen(r, timeout=10)
    errors.append("encode_batch_missing: expected 400")
    print("  FAIL: expected 400")
except urllib.error.HTTPError as e:
    if e.code == 400:
        print(f"  PASS: got 400 as expected")
    else:
        errors.append(f"encode_batch_missing: unexpected {e.code}")
        print(f"  FAIL: unexpected {e.code}")

# 6. 404 for unknown path
print("=== Test 6: GET /unknown (404) ===")
try:
    r = urllib.request.Request(f"{BASE}/unknown", method="GET")
    urllib.request.urlopen(r, timeout=10)
    errors.append("404: expected 404")
    print("  FAIL: expected 404")
except urllib.error.HTTPError as e:
    if e.code == 404:
        print(f"  PASS: got 404 as expected")
    else:
        errors.append(f"404: unexpected {e.code}")
        print(f"  FAIL: unexpected {e.code}")

print(f"\n{'='*40}")
if errors:
    print(f"FAILED: {len(errors)} errors")
    for e in errors:
        print(f"  - {e}")
    sys.exit(1)
else:
    print("ALL 6 TESTS PASSED")
