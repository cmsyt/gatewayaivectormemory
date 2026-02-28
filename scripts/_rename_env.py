"""Batch replace TEAMAIVECTORMEMORY env vars and DB names in scripts/"""
import os

SCRIPTS_DIR = os.path.join(os.path.dirname(__file__))

REPLACEMENTS = [
    ("TEAMAIVECTORMEMORY_PG_URL", "GATEWAYAIVECTORMEMORY_PG_URL"),
    ("TEAMAIVECTORMEMORY_EMBED_URL", "GATEWAYAIVECTORMEMORY_EMBED_URL"),
    ("TEAMAIVECTORMEMORY_TOKEN", "GATEWAYAIVECTORMEMORY_TOKEN"),
    ("TEAMAIVECTORMEMORY_JWT_SECRET", "GATEWAYAIVECTORMEMORY_JWT_SECRET"),
    ("TEAMAIVECTORMEMORY_USER_TOKENS", "GATEWAYAIVECTORMEMORY_USER_TOKENS"),
    ("TEAMAIVECTORMEMORY_USER_ID", "GATEWAYAIVECTORMEMORY_USER_ID"),
    ("postgresql:///teamaivectormemory", "postgresql:///gatewayaivectormemory"),
    ("-m teamaivectormemory ", "-m gatewayaivectormemory "),
]

changed = []
for fname in sorted(os.listdir(SCRIPTS_DIR)):
    fpath = os.path.join(SCRIPTS_DIR, fname)
    if fname.startswith("_") or not os.path.isfile(fpath):
        continue
    try:
        text = open(fpath, "r", encoding="utf-8").read()
    except Exception:
        continue
    original = text
    for old, new in REPLACEMENTS:
        text = text.replace(old, new)
    if text != original:
        open(fpath, "w", encoding="utf-8").write(text)
        changed.append(fname)
        print(f"  ✅ {fname}")

print(f"\nTotal: {len(changed)} files changed")
