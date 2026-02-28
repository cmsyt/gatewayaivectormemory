"""EmbeddingEngine 远程/本地/降级模式自测"""
import os
import sys

os.environ["no_proxy"] = "*"
errors = []

# Test 1: 远程模式 - 设置 EMBEDDING_SERVER_URL
print("=== Test 1: Remote mode ===")
os.environ["EMBEDDING_SERVER_URL"] = "http://127.0.0.1:8900"
from gatewayaivectormemory.embedding.engine import EmbeddingEngine

engine = EmbeddingEngine()
assert engine.is_remote, "Should be remote mode"
engine.load()
assert not engine.ready, "Remote mode should not load local model"

vec = engine.encode("test remote")
assert isinstance(vec, list) and len(vec) == 384, f"Expected 384-dim, got {len(vec)}"
print(f"  PASS: remote encode ok, dim={len(vec)}")

vecs = engine.encode_batch(["hello", "world"])
assert len(vecs) == 2 and all(len(v) == 384 for v in vecs)
print(f"  PASS: remote encode_batch ok, count={len(vecs)}")

# Test 2: 远程不可用 → 降级到本地
print("=== Test 2: Fallback to local ===")
os.environ["EMBEDDING_SERVER_URL"] = "http://127.0.0.1:19999"
engine2 = EmbeddingEngine()
assert engine2.is_remote, "Should start as remote"
engine2.load()

vec2 = engine2.encode("test fallback")
assert not engine2.is_remote, "Should have fallen back to local"
assert engine2.ready, "Local model should be loaded after fallback"
assert isinstance(vec2, list) and len(vec2) == 384
print(f"  PASS: fallback encode ok, dim={len(vec2)}, is_remote={engine2.is_remote}")

# Test 3: 本地模式 - 不设置 EMBEDDING_SERVER_URL
print("=== Test 3: Local mode ===")
os.environ.pop("EMBEDDING_SERVER_URL", None)
engine3 = EmbeddingEngine()
assert not engine3.is_remote, "Should be local mode"
engine3.load()
assert engine3.ready, "Local model should be loaded"

vec3 = engine3.encode("test local")
assert isinstance(vec3, list) and len(vec3) == 384
print(f"  PASS: local encode ok, dim={len(vec3)}")

print(f"\n{'='*40}")
print("ALL 3 ENGINE MODE TESTS PASSED")
