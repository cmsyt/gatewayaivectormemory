"""验证 embedding 模块 import 正常"""
import sys
sys.path.insert(0, ".")

# 测试 engine import
from gatewayaivectormemory.embedding.engine import EmbeddingEngine
e = EmbeddingEngine()
print(f"EmbeddingEngine created, is_remote={e.is_remote}, ready={e.ready}")
assert not e.is_remote, "should be local mode without EMBEDDING_SERVER_URL"
assert not e.ready, "should not be ready before load()"

# 测试 server import
from gatewayaivectormemory.embedding.server import run_embed_server, EmbedHandler
print("embedding.server import OK")

# 测试 config
from gatewayaivectormemory.config import EMBED_DEFAULT_PORT
assert EMBED_DEFAULT_PORT == 8900, f"expected 8900, got {EMBED_DEFAULT_PORT}"
print(f"EMBED_DEFAULT_PORT={EMBED_DEFAULT_PORT}")

# 测试 CLI argparse
from gatewayaivectormemory.__main__ import main
print("__main__ import OK")

print("\nAll import tests passed!")
