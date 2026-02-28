"""Replace CLI command 'run' -> 'team-run' in README and docs"""
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

replacements = [
    ("run install", "team-run install"),
    ("run web ", "team-run web "),
    ("run web\n", "team-run web\n"),
    ("`run install`", "`team-run install`"),
]

count = 0
for f in files:
    if not f.exists():
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
