"""Batch replace aivectormemory -> gatewayaivectormemory in source files"""
import re
from pathlib import Path

ROOT = Path(__file__).parent.parent

# Files to process (source code only, not docs/README yet)
source_files = list(ROOT.glob("gatewayaivectormemory/**/*.py"))

count = 0
for f in source_files:
    if "__pycache__" in str(f):
        continue
    text = f.read_text("utf-8")
    # Replace import paths and string references
    new_text = text.replace("from aivectormemory.", "from gatewayaivectormemory.")
    new_text = new_text.replace("import aivectormemory", "import gatewayaivectormemory")
    new_text = new_text.replace('"aivectormemory"', '"gatewayaivectormemory"')
    new_text = new_text.replace("[aivectormemory]", "[gatewayaivectormemory]")
    new_text = new_text.replace("aivectormemory install", "gatewayaivectormemory install")
    new_text = new_text.replace('"-m", "aivectormemory"', '"-m", "gatewayaivectormemory"')
    new_text = new_text.replace('"aivectormemory@latest"', '"gatewayaivectormemory@latest"')
    new_text = new_text.replace(".aivectormemory", ".gatewayaivectormemory")
    new_text = new_text.replace("aivectormemory-pre-tool-check", "gatewayaivectormemory-pre-tool-check")
    new_text = new_text.replace("aivectormemory-steering", "gatewayaivectormemory-steering")
    new_text = new_text.replace("/aivectormemory.md", "/gatewayaivectormemory.md")
    new_text = new_text.replace("pip install aivectormemory", "pip install gatewayaivectormemory")
    new_text = new_text.replace('"""aivectormemory', '"""gatewayaivectormemory')
    if new_text != text:
        f.write_text(new_text, "utf-8")
        count += 1
        print(f"  ✓ {f.relative_to(ROOT)}")

print(f"\nUpdated {count} source files")
