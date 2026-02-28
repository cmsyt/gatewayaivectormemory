# 设计文档：Embedding 共享服务

## 1. 架构概览

```
┌─────────────────────────────────────────────────┐
│  team-run embed-server --port 8900              │
│  ┌───────────────────────────────────────────┐  │
│  │  EmbedHTTPServer (http.server.HTTPServer) │  │
│  │  ├── POST /encode       → 单文本编码      │  │
│  │  ├── POST /encode_batch → 批量编码        │  │
│  │  └── GET  /health       → 健康检查        │  │
│  │                                           │  │
│  │  EmbeddingEngine（进程内，单实例）          │  │
│  └───────────────────────────────────────────┘  │
└─────────────────────────────────────────────────┘
         ▲
         │ HTTP (JSON)
         │
┌────────┴────────────────────────────────────────┐
│  MCP Worker (team-run)                          │
│  EMBEDDING_SERVER_URL=http://127.0.0.1:8900     │
│                                                 │
│  EmbeddingEngine.encode(text)                   │
│    → 检测 EMBEDDING_SERVER_URL                   │
│    → 有：HTTP POST /encode（不加载本地模型）      │
│    → 无：本地 ONNX 推理（现有行为）               │
└─────────────────────────────────────────────────┘
```

## 2. 模块设计

### 2.1 EmbeddingEngine 改造

现有 `EmbeddingEngine` 改为双模式，通过环境变量 `EMBEDDING_SERVER_URL` 自动切换：

```python
class EmbeddingEngine:
    def __init__(self):
        self._server_url = os.environ.get("EMBEDDING_SERVER_URL")  # 新增
        self._session = None
        self._tokenizer = None
        self._encode_cached = lru_cache(maxsize=1024)(self._encode_impl)
        self._remote_failed = False  # 降级标记

    @property
    def is_remote(self) -> bool:
        return bool(self._server_url) and not self._remote_failed

    def load(self):
        """远程模式跳过本地模型加载"""
        if self._server_url and not self._remote_failed:
            print(f"[teamaivectormemory] Remote embedding: {self._server_url}", file=sys.stderr)
            return
        # 原有本地加载逻辑不变
        ...

    def encode(self, text: str) -> list[float]:
        if self.is_remote:
            return self._encode_remote(text)
        if not self.ready:
            self.load()
        return list(self._encode_cached(text))

    def _encode_remote(self, text: str) -> list[float]:
        """HTTP 调用 embed-server"""
        import urllib.request, json
        url = f"{self._server_url}/encode"
        data = json.dumps({"text": text}).encode()
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read())["vector"]
        except Exception as e:
            print(f"[teamaivectormemory] Remote embedding failed, fallback to local: {e}", file=sys.stderr)
            self._remote_failed = True
            self.load()  # 降级：加载本地模型
            return self.encode(text)

    def _encode_remote_batch(self, texts: list[str]) -> list[list[float]]:
        """HTTP 调用 embed-server 批量接口"""
        import urllib.request, json
        url = f"{self._server_url}/encode_batch"
        data = json.dumps({"texts": texts}).encode()
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read())["vectors"]
        except Exception as e:
            print(f"[teamaivectormemory] Remote batch failed, fallback to local: {e}", file=sys.stderr)
            self._remote_failed = True
            self.load()
            return self.encode_batch(texts)

    def encode_batch(self, texts: list[str]) -> list[list[float]]:
        if self.is_remote:
            return self._encode_remote_batch(texts)
        return [self.encode(t) for t in texts]
```

设计要点：
- 零依赖：远程调用只用 `urllib.request`，不引入 requests/httpx
- 降级一次性：`_remote_failed = True` 后本会话不再尝试远程，避免反复超时
- LRU 缓存保留：本地模式缓存不变，远程模式不走缓存（服务端可自行缓存）
- 无状态：不绑定 user_id/scope，为后续扩展预留

### 2.2 embed-server HTTP 服务

新增 `teamaivectormemory/embedding/server.py`：

```python
# teamaivectormemory/embedding/server.py
import json, sys, os
from http.server import HTTPServer, BaseHTTPRequestHandler
from teamaivectormemory.embedding.engine import EmbeddingEngine

class EmbedHandler(BaseHTTPRequestHandler):
    engine: EmbeddingEngine = None

    def do_POST(self):
        if self.path == "/encode":
            self._handle_encode()
        elif self.path == "/encode_batch":
            self._handle_encode_batch()
        else:
            self.send_error(404)

    def do_GET(self):
        if self.path == "/health":
            self._handle_health()
        else:
            self.send_error(404)

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", 0))
        return json.loads(self.rfile.read(length)) if length else {}

    def _send_json(self, data: dict, status: int = 200):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def _handle_encode(self):
        body = self._read_json()
        text = body.get("text", "")
        if not text:
            self._send_json({"error": "missing 'text'"}, 400)
            return
        vector = self.engine.encode(text)
        self._send_json({"vector": vector, "dimension": len(vector)})

    def _handle_encode_batch(self):
        body = self._read_json()
        texts = body.get("texts", [])
        if not texts:
            self._send_json({"error": "missing 'texts'"}, 400)
            return
        vectors = self.engine.encode_batch(texts)
        self._send_json({"vectors": vectors, "dimension": len(vectors[0]) if vectors else 0})

    def _handle_health(self):
        self._send_json({
            "status": "ok" if self.engine.ready else "loading",
            "model": "multilingual-e5-small",
            "dimension": 384
        })

    def log_message(self, format, *args):
        print(f"[teamaivectormemory-embed] {args[0]}", file=sys.stderr)


def run_embed_server(port: int = 8900, bind: str = "127.0.0.1", daemon: bool = False):
    # embed-server 自身不设 EMBEDDING_SERVER_URL，强制本地模式
    os.environ.pop("EMBEDDING_SERVER_URL", None)

    engine = EmbeddingEngine()
    engine.load()
    EmbedHandler.engine = engine

    server = HTTPServer((bind, port), EmbedHandler)
    print(f"[teamaivectormemory] Embed server: http://{bind}:{port}", file=sys.stderr)

    if daemon:
        if not hasattr(os, "fork"):
            print("[teamaivectormemory] --daemon not supported on Windows", file=sys.stderr)
            sys.exit(1)
        pid = os.fork()
        if pid > 0:
            print(f"[teamaivectormemory] Running in background (PID {pid})", file=sys.stderr)
            sys.exit(0)
        os.setsid()
        sys.stdin.close()
        devnull = open(os.devnull, "w")
        sys.stdout = devnull
        sys.stderr = devnull

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
```

设计要点：
- 复用 `http.server.HTTPServer`，与 web dashboard 同一模式
- `os.environ.pop("EMBEDDING_SERVER_URL", None)` 防止 embed-server 自身递归调用远程
- daemon 实现与 `web/app.py` 一致（`os.fork` + `os.setsid`）
- 无数据库依赖，纯计算服务

### 2.3 CLI 改造（`__main__.py`）

新增 `embed-server` 子命令：

```python
embed_parser = sub.add_parser("embed-server", help="启动 Embedding 共享服务")
embed_parser.add_argument("--port", type=int, default=8900, help="服务端口")
embed_parser.add_argument("--bind", default="127.0.0.1", help="绑定地址")
embed_parser.add_argument("--daemon", action="store_true", default=False, help="后台运行")
```

处理分支：

```python
elif args.command == "embed-server":
    from teamaivectormemory.embedding.server import run_embed_server
    run_embed_server(port=args.port, bind=args.bind, daemon=args.daemon)
```

## 3. API 接口规范

### POST /encode

请求：
```json
{"text": "要编码的文本"}
```

响应：
```json
{"vector": [0.012, -0.034, ...], "dimension": 384}
```

### POST /encode_batch

请求：
```json
{"texts": ["文本1", "文本2"]}
```

响应：
```json
{"vectors": [[0.012, ...], [0.056, ...]], "dimension": 384}
```

### GET /health

响应：
```json
{"status": "ok", "model": "multilingual-e5-small", "dimension": 384}
```

错误响应（所有接口）：
```json
{"error": "错误描述"}
```

## 4. 容错与降级

```
EmbeddingEngine.encode(text)
  ├── EMBEDDING_SERVER_URL 未设置 → 本地模式（不变）
  └── EMBEDDING_SERVER_URL 已设置
      ├── HTTP 成功 → 返回远程结果
      └── HTTP 失败（超时/连接拒绝/5xx）
          ├── _remote_failed = True
          ├── 打印警告到 stderr
          ├── 自动 load() 加载本地模型
          └── 用本地模式重新编码（本会话后续全走本地）
```

- HTTP 超时：10 秒
- 降级策略：一次失败后永久降级（本进程生命周期内），不反复重试
- 降级日志：`[teamaivectormemory] Remote embedding failed, fallback to local: {error}`

## 5. 文件变更清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `teamaivectormemory/embedding/engine.py` | 修改 | 添加远程模式、降级逻辑 |
| `teamaivectormemory/embedding/server.py` | 新增 | embed-server HTTP 服务 |
| `teamaivectormemory/__main__.py` | 修改 | 添加 `embed-server` 子命令 |
| `teamaivectormemory/config.py` | 修改 | 添加 `EMBED_DEFAULT_PORT = 8900` |

## 6. 不改动的部分

- `server.py`（MCP Server）：不改，`EmbeddingEngine` 内部自动切换模式
- `db/` 目录：不改，数据库层不涉及
- `web/`：不改，web dashboard 独立
- `tools/`：不改，工具层通过 engine 接口调用，透明切换
