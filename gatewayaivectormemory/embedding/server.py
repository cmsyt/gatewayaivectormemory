import json
import os
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from gatewayaivectormemory.embedding.engine import EmbeddingEngine
from gatewayaivectormemory.config import MODEL_NAME, MODEL_DIMENSION, EMBED_DEFAULT_PORT


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
            "model": MODEL_NAME,
            "dimension": MODEL_DIMENSION
        })

    def log_message(self, format, *args):
        print(f"[gatewayaivectormemory-embed] {args[0]}", file=sys.stderr)


def run_embed_server(port: int = EMBED_DEFAULT_PORT, bind: str = "127.0.0.1", daemon: bool = False):
    os.environ.pop("EMBEDDING_SERVER_URL", None)

    engine = EmbeddingEngine()
    engine.load()
    EmbedHandler.engine = engine

    server = HTTPServer((bind, port), EmbedHandler)
    print(f"[gatewayaivectormemory] Embed server: http://{bind}:{port}", file=sys.stderr)

    if daemon:
        if not hasattr(os, "fork"):
            print("[gatewayaivectormemory] --daemon not supported on Windows", file=sys.stderr)
            sys.exit(1)
        pid = os.fork()
        if pid > 0:
            print(f"[gatewayaivectormemory] Running in background (PID {pid})", file=sys.stderr)
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
