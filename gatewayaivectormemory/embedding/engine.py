import json
import os
import sys
import urllib.request
import numpy as np
from functools import lru_cache
from pathlib import Path
from gatewayaivectormemory.config import MODEL_NAME, MODEL_DIMENSION


class EmbeddingEngine:
    def __init__(self):
        self._server_url = os.environ.get("EMBEDDING_SERVER_URL", "").rstrip("/") or None
        self._session = None
        self._tokenizer = None
        self._remote_failed = False
        self._encode_cached = lru_cache(maxsize=1024)(self._encode_impl)

    @property
    def ready(self) -> bool:
        return self._session is not None

    @property
    def is_remote(self) -> bool:
        return bool(self._server_url) and not self._remote_failed

    def load(self):
        if self.is_remote:
            print(f"[gatewayaivectormemory] Remote embedding: {self._server_url}", file=sys.stderr)
            return
        if self.ready:
            return
        try:
            from huggingface_hub import hf_hub_download
            from tokenizers import Tokenizer
            import onnxruntime as ort

            model_dir = self._download_model(hf_hub_download)
            self._tokenizer = Tokenizer.from_file(str(model_dir / "tokenizer.json"))
            self._tokenizer.enable_padding()
            self._tokenizer.enable_truncation(max_length=512)

            model_path = model_dir / "model.onnx"
            if not model_path.exists():
                model_path = model_dir / "onnx" / "model.onnx"

            self._session = ort.InferenceSession(
                str(model_path),
                providers=["CPUExecutionProvider"]
            )
            print(f"[gatewayaivectormemory] Embedding model loaded: {MODEL_NAME}", file=sys.stderr)
        except Exception as e:
            print(f"[gatewayaivectormemory] Failed to load embedding model: {e}", file=sys.stderr)
            raise

    def _download_model(self, hf_hub_download) -> Path:
        from huggingface_hub import snapshot_download
        model_dir = Path(snapshot_download(
            MODEL_NAME,
            allow_patterns=["tokenizer.json", "tokenizer_config.json",
                           "model.onnx", "onnx/model.onnx",
                           "special_tokens_map.json", "config.json"]
        ))
        return model_dir

    def encode(self, text: str) -> list[float]:
        if self.is_remote:
            return self._encode_remote(text)
        if not self.ready:
            self.load()
        return list(self._encode_cached(text))

    def _encode_remote(self, text: str) -> list[float]:
        url = f"{self._server_url}/encode"
        data = json.dumps({"text": text}).encode()
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read())["vector"]
        except Exception as e:
            print(f"[gatewayaivectormemory] Remote embedding failed, fallback to local: {e}", file=sys.stderr)
            self._remote_failed = True
            self.load()
            return self.encode(text)

    def _encode_remote_batch(self, texts: list[str]) -> list[list[float]]:
        url = f"{self._server_url}/encode_batch"
        data = json.dumps({"texts": texts}).encode()
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read())["vectors"]
        except Exception as e:
            print(f"[gatewayaivectormemory] Remote batch failed, fallback to local: {e}", file=sys.stderr)
            self._remote_failed = True
            self.load()
            return self.encode_batch(texts)

    def _encode_impl(self, text: str) -> tuple[float, ...]:
        prefixed = f"query: {text}"
        encoded = self._tokenizer.encode(prefixed)

        input_ids = np.array([encoded.ids], dtype=np.int64)
        attention_mask = np.array([encoded.attention_mask], dtype=np.int64)
        token_type_ids = np.zeros_like(input_ids)

        outputs = self._session.run(
            None,
            {"input_ids": input_ids, "attention_mask": attention_mask, "token_type_ids": token_type_ids}
        )

        hidden = outputs[0]
        mask_expanded = attention_mask[:, :, np.newaxis].astype(np.float32)
        summed = (hidden * mask_expanded).sum(axis=1)
        counts = mask_expanded.sum(axis=1).clip(min=1e-9)
        pooled = summed / counts

        norm = np.linalg.norm(pooled, axis=1, keepdims=True).clip(min=1e-9)
        normalized = (pooled / norm)[0]

        return tuple(normalized.tolist())

    def encode_batch(self, texts: list[str]) -> list[list[float]]:
        if self.is_remote:
            return self._encode_remote_batch(texts)
        return [self.encode(t) for t in texts]
