import os
from pathlib import Path

# PostgreSQL
PG_URL = os.environ.get("GATEWAYAIVECTORMEMORY_PG_URL", "")
EMBED_URL = os.environ.get("GATEWAYAIVECTORMEMORY_EMBED_URL", "")

# Embedding
MODEL_NAME = "intfloat/multilingual-e5-small"
MODEL_DIMENSION = 384
DEDUP_THRESHOLD = 0.95

# Defaults
USER_SCOPE_DIR = "@user@"
DEFAULT_TOP_K = 5
WEB_DEFAULT_PORT = 9080
EMBED_DEFAULT_PORT = 8900


def get_project_dir(project_dir: str | None = None) -> str:
    return str(Path(project_dir).resolve()) if project_dir else str(Path.cwd().resolve())
