"""测试本地模式不受影响 + 降级逻辑"""
import os
import sys
sys.path.insert(0, ".")

# === 测试1: 本地模式（不设 EMBEDDING_SERVER_URL）===
os.environ.pop("EMBEDDING_SERVER_URL", None)
print("=== 本地模式 ===")

from gatewayaivectormemory.embedding.engine import EmbeddingEngine

e1 = EmbeddingEngine()
assert not e1.is_remote, "should be local"
vec = e1.encode("hello")
assert len(vec) == 384
print(f"Local encode: len={len(vec)}, is_remote={e1.is_remote}, ready={e1.ready}")
assert e1.ready, "should have loaded local model"
print("Local mode - PASS\n")

# === 测试2: 降级（指向不存在的服务）===
print("=== 降级测试 ===")
os.environ["EMBEDDING_SERVER_URL"] = "http://127.0.0.1:19999"
os.environ["no_proxy"] = "127.0.0.1,localhost"

e2 = EmbeddingEngine()
assert e2.is_remote, "should start as remote"
print(f"Before encode: is_remote={e2.is_remote}, ready={e2.ready}")

vec2 = e2.encode("fallback test")
print(f"After encode: is_remote={e2.is_remote}, ready={e2.ready}, len={len(vec2)}")
assert not e2.is_remote, "should have fallen back to local"
assert e2.ready, "should have loaded local model after fallback"
assert len(vec2) == 384
print("Fallback - PASS\n")

print("All local + fallback tests passed!")
