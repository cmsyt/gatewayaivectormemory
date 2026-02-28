"""Batch replace remaining aivectormemory references in all project files"""
from pathlib import Path

ROOT = Path(__file__).parent.parent

# All files that still have old references
files = [
    # Source code
    ROOT / "gatewayaivectormemory/web/app.py",
    ROOT / "gatewayaivectormemory/server.py",
    ROOT / "gatewayaivectormemory/__init__.py",
    ROOT / "gatewayaivectormemory/__main__.py",
    ROOT / "gatewayaivectormemory/hooks/check_track.sh",
    ROOT / "gatewayaivectormemory/tools/readme.py",
    # Web static
    ROOT / "gatewayaivectormemory/web/static/index.html",
    ROOT / "gatewayaivectormemory/web/static/app.js",
    ROOT / "gatewayaivectormemory/web/static/i18n.js",
    ROOT / "gatewayaivectormemory/web/static/style.css",
    # Scripts
    ROOT / "scripts/test_mcp_connect.py",
    ROOT / "scripts/test_mcp_stdio.py",
    # Project files
    ROOT / "NOTICE",
    ROOT / "LICENSE",
    ROOT / "pyproject.toml",
]

# Ordered replacements (specific first)
replacements = [
    # Fix server.py wrong import
    ("from aivectormemory import", "from gatewayaivectormemory import"),
    # DB path
    ('$HOME/.aivectormemory/', '$HOME/.gatewayaivectormemory/'),
    ('~/.aivectormemory/', '~/.gatewayaivectormemory/'),
    # Module references
    ('"-m", "aivectormemory"', '"-m", "gatewayaivectormemory"'),
    ('-m aivectormemory', '-m gatewayaivectormemory'),
    ('"aivectormemory"', '"gatewayaivectormemory"'),
    # Log prefixes
    ("[aivectormemory-web]", "[gatewayaivectormemory-web]"),
    ("[aivectormemory]", "[gatewayaivectormemory]"),
    # Display names - keep AIVectorMemory as brand name but prefix with Team
    ("AIVectorMemory", "TeamAIVectorMemory"),
    # URL fix
    ("Edlineas/aivectormemory", "cmsyt/gatewayaivectormemory"),
    ("Edlineas/gatewayaivectormemory", "cmsyt/gatewayaivectormemory"),
    # Command references
    ("aivectormemory install", "gatewayaivectormemory install"),
    ("aivectormemory-export", "gatewayaivectormemory-export"),
    # Old project dir references in test scripts
    ("/Users/macos/item/run-memory-mcp-server", "/Users/macos/item/team-run-memory-mcp-server"),
    # Fix any double Team
    ("TeamTeamAIVectorMemory", "TeamAIVectorMemory"),
]

count = 0
for f in files:
    if not f.exists():
        print(f"  ⚠ {f.relative_to(ROOT)} not found")
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
