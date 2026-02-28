"""readme 工具 - 从代码和配置自动生成 README 内容"""
import json
from pathlib import Path


SUPPORTED_LANGS = {
    "en": "docs/README.en.md",
    "zh-TW": "docs/README.zh-TW.md",
    "ja": "docs/README.ja.md",
    "de": "docs/README.de.md",
    "fr": "docs/README.fr.md",
    "es": "docs/README.es.md",
}

LANG_LABELS = {
    "en": "English",
    "zh-TW": "繁體中文",
    "ja": "日本語",
    "de": "Deutsch",
    "fr": "Français",
    "es": "Español",
}


def _load_pyproject() -> dict:
    p = Path(__file__).parent.parent.parent / "pyproject.toml"
    if not p.exists():
        return {}
    text = p.read_text("utf-8")
    result = {}
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("version"):
            result["version"] = line.split("=", 1)[1].strip().strip('"')
        elif line.startswith("description"):
            result["description"] = line.split("=", 1)[1].strip().strip('"')
        elif line.startswith("requires-python"):
            result["requires_python"] = line.split("=", 1)[1].strip().strip('"')
    deps = []
    in_deps = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("dependencies"):
            in_deps = True
            continue
        if in_deps:
            if stripped == "]":
                break
            dep = stripped.strip('",').strip()
            if dep:
                deps.append(dep)
    result["dependencies"] = deps
    return result


def _extract_tools() -> list[dict]:
    from gatewayaivectormemory.tools import TOOL_DEFINITIONS
    tools = []
    for t in TOOL_DEFINITIONS:
        props = t.get("inputSchema", {}).get("properties", {})
        required = t.get("inputSchema", {}).get("required", [])
        params = []
        for k, v in props.items():
            typ = v.get("type", "string")
            if isinstance(typ, list):
                typ = "/".join(typ)
            desc = v.get("description", "")
            req = "(required)" if k in required else ""
            params.append({"name": k, "type": typ, "description": desc, "required": req})
        tools.append({"name": t["name"], "description": t["description"], "params": params})
    return tools


def _generate_tools_section(tools: list[dict]) -> str:
    lines = [f"## 🛠️ {len(tools)} MCP Tools\n"]
    for t in tools:
        lines.append(f"### `{t['name']}` — {t['description'].split('。')[0]}\n")
        lines.append("```")
        for p in t["params"]:
            req = " (required)" if p["required"] else ""
            lines.append(f"{p['name']:20s} ({p['type']}{req})  {p['description']}")
        lines.append("```\n")
    return "\n".join(lines)


def _generate_deps_section(pyproject: dict) -> str:
    lines = ["## 📦 Tech Stack\n", "| Component | Technology |", "|-----------|-----------|"]
    lines.append(f"| Runtime | Python {pyproject.get('requires_python', '>= 3.10')} |")
    lines.append("| Vector DB | PostgreSQL + pgvector |")
    lines.append("| Embedding | ONNX Runtime + intfloat/multilingual-e5-small |")
    lines.append("| Tokenizer | HuggingFace Tokenizers |")
    lines.append("| HTTP API | FastAPI + Uvicorn |")
    lines.append("| Web | FastAPI + Vanilla JS |")
    return "\n".join(lines)


def _generate_content(lang: str, sections: list[str] | None = None) -> str:
    pyproject = _load_pyproject()
    tools = _extract_tools()
    all_sections = {
        "header": f"# 🧠 GatewayAIVectorMemory v{pyproject.get('version', '?')}\n\n{pyproject.get('description', '')}",
        "tools": _generate_tools_section(tools),
        "deps": _generate_deps_section(pyproject),
    }
    if sections:
        parts = [all_sections[s] for s in sections if s in all_sections]
    else:
        parts = list(all_sections.values())
    content = "\n\n---\n\n".join(parts)
    return f"<!-- Generated for lang={lang} -->\n\n{content}"


def _diff_content(lang: str) -> dict:
    generated = _generate_content(lang)
    readme_path = SUPPORTED_LANGS.get(lang)
    if not readme_path:
        return {"error": f"Unsupported language: {lang}", "supported": list(SUPPORTED_LANGS.keys())}
    p = Path(__file__).parent.parent.parent / readme_path
    if not p.exists():
        return {"status": "missing", "path": readme_path, "generated_length": len(generated), "generated": generated}
    current = p.read_text("utf-8")
    tools = _extract_tools()
    tool_names_gen = {t["name"] for t in tools}
    tool_names_cur = set()
    for line in current.splitlines():
        if line.startswith("### `") and "`" in line[5:]:
            name = line[5:line.index("`", 5)]
            tool_names_cur.add(name)
    missing_tools = tool_names_gen - tool_names_cur
    extra_tools = tool_names_cur - tool_names_gen
    pyproject = _load_pyproject()
    version = pyproject.get("version", "")
    version_in_readme = version in current if version else None
    return {
        "status": "exists",
        "path": readme_path,
        "current_length": len(current),
        "generated_length": len(generated),
        "missing_tools": sorted(missing_tools),
        "extra_tools": sorted(extra_tools),
        "version_match": version_in_readme,
        "current_version": version,
        "generated": generated,
    }


def handle_readme(args: dict, cm, **_) -> dict:
    action = args.get("action", "generate")
    lang = args.get("lang", "en")
    if action == "generate":
        sections = args.get("sections")
        content = _generate_content(lang, sections)
        return {"content": content, "lang": lang, "supported_langs": list(SUPPORTED_LANGS.keys())}
    elif action == "diff":
        return _diff_content(lang)
    return {"error": f"Unknown action: {action}", "valid_actions": ["generate", "diff"]}
