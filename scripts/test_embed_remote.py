"""测试 EmbeddingEngine 远程模式"""
import os
import sys
sys.path.insert(0, ".")

# 设置远程 URL 指向正在运行的 embed-server
os.environ["EMBEDDING_SERVER_URL"] = "http://127.0.0.1:8901"

from gatewayaivectormemory.embedding.engine import EmbeddingEngine

e = EmbeddingEngine()
print(f"is_remote={e.is_remote}, ready={e.ready}")
assert e.is_remote, "should be remote mode"
assert not e.ready, "should not have local model loaded"

# load() 应该跳过本地模型
e.load()
assert not e.ready, "should still not have local model after load() in remote mode"
print("load() skipped local model - OK")

# encode 应该走 HTTP
vec = e.encode("hello world")
print(f"encode result: len={len(vec)}, type={type(vec[0])}")
assert len(vec) == 384
assert isinstance(vec[0], float)
print("Remote encode - PASS")

# encode_batch 应该走 HTTP
vecs = e.encode_batch(["hello", "world"])
print(f"encode_batch result: count={len(vecs)}, dim={len(vecs[0])}")
assert len(vecs) == 2
assert all(len(v) == 384 for v in vecs)
print("Remote encode_batch - PASS")

print("\nAll remote mode tests passed!")
