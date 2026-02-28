"""测试 EmbeddingEngine 远程模式 - 用 no_proxy 绕过代理"""
import os
import sys
sys.path.insert(0, ".")

# 绕过代理
os.environ["no_proxy"] = "127.0.0.1,localhost"
os.environ["NO_PROXY"] = "127.0.0.1,localhost"
os.environ["EMBEDDING_SERVER_URL"] = "http://127.0.0.1:8901"

from gatewayaivectormemory.embedding.engine import EmbeddingEngine

e = EmbeddingEngine()
print(f"is_remote={e.is_remote}, ready={e.ready}")
assert e.is_remote, "should be remote mode"

e.load()
assert not e.ready, "should not have local model"
print("load() skipped local model - OK")

vec = e.encode("hello world")
print(f"encode: len={len(vec)}, is_remote_after={e.is_remote}")
assert len(vec) == 384
assert e.is_remote, "should still be remote (no fallback)"
print("Remote encode - PASS")

vecs = e.encode_batch(["hello", "world"])
print(f"encode_batch: count={len(vecs)}, dim={len(vecs[0])}")
assert len(vecs) == 2
print("Remote encode_batch - PASS")

print("\nAll remote mode tests passed (no proxy)!")
