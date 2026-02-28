"""Batch replace aivectormemory -> gatewayaivectormemory in README and docs files"""
from pathlib import Path

ROOT = Path(__file__).parent.parent

files = [
    ROOT / "README.md",
    ROOT / "docs/README.zh-TW.md",
    ROOT / "docs/README.en.md",
    ROOT / "docs/README.es.md",
    ROOT / "docs/README.de.md",
    ROOT / "docs/README.fr.md",
    ROOT / "docs/README.ja.md",
]

# Replacements in order (more specific first to avoid double-replacing)
replacements = [
    # Already-correct forms should not be touched, so we replace specific patterns
    ("gatewayaivectormemory", "PLACEHOLDER_TEAM"),  # protect existing
    ("AIVectorMemory", "TeamAIVectorMemory"),
    ("aivectormemory", "gatewayaivectormemory"),
    ("Edlineas/gatewayaivectormemory", "cmsyt/gatewayaivectormemory"),  # fix URL
    ("PLACEHOLDER_TEAM", "gatewayaivectormemory"),  # restore
    ("TeamTeamAIVectorMemory", "TeamAIVectorMemory"),  # fix double
    ("~/.gatewayaivectormemory", "~/.gatewayaivectormemory"),  # already correct
]

count = 0
for f in files:
    if not f.exists():
        print(f"  ⚠ {f.name} not found, skipping")
        continue
    text = f.read_text("utf-8")
    new_text = text
    for old, new in replacements:
        new_text = new_text.replace(old, new)
    if new_text != text:
        f.write_text(new_text, "utf-8")
        count += 1
        print(f"  ✓ {f.relative_to(ROOT)}")
    else:
        print(f"  - {f.relative_to(ROOT)} (no changes)")

print(f"\nUpdated {count} files")
