🌐 [简体中文](../README.md) | [繁體中文](README.zh-TW.md) | English | [Español](README.es.md) | [Deutsch](README.de.md) | [Français](README.fr.md) | [日本語](README.ja.md)

<p align="center">
  <h1 align="center">🧠 GatewayAIVectorMemory</h1>
  <p align="center">
    <strong>Give your AI coding assistant a team memory — PostgreSQL + pgvector storage · HTTP Memory Proxy · Multi-user collaboration & knowledge sharing</strong>
  </p>
  <p align="center">
    <a href="https://pypi.org/project/gatewayaivectormemory/"><img src="https://img.shields.io/pypi/v/gatewayaivectormemory?color=blue&label=PyPI" alt="PyPI"></a>
    <a href="https://pypi.org/project/gatewayaivectormemory/"><img src="https://img.shields.io/pypi/pyversions/gatewayaivectormemory" alt="Python"></a>
    <a href="https://github.com/cmsyt/gatewayaivectormemory/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-Apache_2.0-green" alt="License"></a>
  </p>
</p>

---

> **Sound familiar?** Every new session, your AI starts from scratch — project conventions you taught it yesterday? Forgotten. Pitfalls it already hit? It'll hit them again. Half-finished work? Gone. Worse, every team member keeps hitting the same pitfalls independently, knowledge never accumulates, experience never transfers.
>
> **GatewayAIVectorMemory is the AI memory hub built for teams.** PostgreSQL + pgvector storage, HTTP Memory Proxy for unified access, team pitfall experiences auto-shared, architectural knowledge deposited by one benefits all, multi-user data strictly isolated. Supports multi-worker shared Embedding model: N processes, 1 copy of memory. New sessions auto-restore context, semantic search retrieves exactly what's needed, token usage drops 50%+.

## ✨ Core Features

| Feature | Description |
|---------|-------------|
| 👥 **Team Knowledge Sharing** | One person's pitfall becomes everyone's lesson — team memories auto-shared, architectural knowledge and lessons learned become team assets |
| 🔐 **Multi-User Data Isolation** | Multiple users on one server, personal memories strictly isolated and invisible to others, team memories shared by project |
| ⚡ **Shared Embedding Service** | N workers share one Embedding model, 200MB × N → 200MB × 1, memory drops 90% |
| 🧠 **Cross-Session Memory** | Pitfalls, decisions, conventions all persist across sessions |
| 🔍 **Semantic Search** | Search "database timeout" and find "connection pool issue" — no need to recall exact wording |
| 💰 **Save 50%+ Tokens** | Semantic retrieval on demand, no more bulk context injection |
| 🔗 **Task-Driven Dev** | Issue tracking → task breakdown → status sync → linked archival. AI manages the full dev workflow |
| 📊 **Web Dashboard** | Visual management for all memories and tasks, 3D vector network reveals knowledge connections |
| 🔌 **All IDEs** | Cursor / Kiro / Claude Code / Windsurf / VSCode / OpenCode / Trae — via HTTP API |
| 🔄 **Smart Dedup** | Similarity > 0.95 auto-merges updates, keeping your memory store clean |

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────┐
│                   AI IDE                         │
│  Cursor / Kiro / Claude Code / Windsurf / ...   │
└──────────────────────┬──────────────────────────┘
                       │ HTTP API
┌──────────────────────▼──────────────────────────┐
│           Memory Proxy (FastAPI + Uvicorn)       │
│                                                  │
│  POST /memory/remember  POST /memory/recall      │
│  POST /memory/forget    POST /memory/status      │
│  POST /memory/track     POST /memory/task        │
│  POST /memory/auto_save POST /memory/readme      │
│  GET  /memory/health                             │
│                                                  │
│  ┌──────────────┐  ┌───────────────────────────┐ │
│  │ Auth Layer   │  │  X-User-Id / X-Project-Dir│ │
│  │ Token/JWT    │  │  Multi-user isolation     │ │
│  └──────────────┘  └───────────────────────────┘ │
└──────────┬───────────────────┬───────────────────┘
           │                   │
┌──────────▼──────────┐ ┌─────▼─────────────────┐
│  Embedding Server   │ │  PostgreSQL + pgvector │
│  (ONNX Runtime)     │ │  Vector storage +      │
│  HTTP :8900         │ │  full-text search      │
└─────────────────────┘ └───────────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- Python >= 3.10
- PostgreSQL >= 14 (with pgvector extension)
- Install pgvector: `CREATE EXTENSION IF NOT EXISTS vector;`

### Install

```bash
pip install gatewayaivectormemory
```

### 1. Start Embedding Shared Service

```bash
# Default port 8900
team-run embed-server

# Specify port + run in background
team-run embed-server --port 8900 --daemon

# Allow remote access
team-run embed-server --bind 0.0.0.0 --port 8900
```

> The Embedding model (~200MB) is auto-downloaded on first run. Users in China can set `export HF_ENDPOINT=https://hf-mirror.com` to speed up.

### 2. Start Memory Proxy

```bash
team-run memory-proxy \
  --pg-url "postgresql://user:pass@localhost:5432/dbname" \
  --embed-url "http://127.0.0.1:8900" \
  --port 8080 \
  --workers 4
```

Authentication options (mutually exclusive):

```bash
# Static Token auth
team-run memory-proxy --pg-url "..." --token "your-secret-token"

# JWT auth
team-run memory-proxy --pg-url "..." --jwt-secret "your-jwt-secret"

# User token mapping file
team-run memory-proxy --pg-url "..." --user-tokens "/path/to/tokens.json"
```

### 3. Configure IDE

Add to your IDE's MCP config file:

```json
{
  "mcpServers": {
    "memory": {
      "type": "http",
      "url": "http://127.0.0.1:8080/memory",
      "headers": {
        "Authorization": "Bearer your-secret-token",
        "X-User-Id": "your-user-id",
        "X-Project-Dir": "/path/to/your/project"
      }
    }
  }
}
```

<details>
<summary>📍 IDE Config File Locations</summary>

| IDE | Config Path |
|-----|------------|
| Kiro | `.kiro/settings/mcp.json` |
| Cursor | `.cursor/mcp.json` |
| Claude Code | `.mcp.json` |
| Windsurf | `.windsurf/mcp.json` |
| VSCode | `.vscode/mcp.json` |
| Trae | `.trae/mcp.json` |
| OpenCode | `opencode.json` |

</details>

## 📊 Web Dashboard

```bash
team-run web --pg-url "postgresql://user:pass@localhost:5432/dbname" --port 9080
team-run web --pg-url "..." --embed-url "http://127.0.0.1:8900" --port 9080
team-run web --pg-url "..." --port 9080 --quiet          # Suppress request logs
team-run web --pg-url "..." --port 9080 --quiet --daemon  # Run in background
team-run web --pg-url "..." --token "secret" --port 9080  # Token auth
team-run web --pg-url "..." --user-id "alice" --port 9080 # Specify user (omit = admin mode)
```

Visit `http://localhost:9080` in your browser.

- Multi-project switching, memory browse/search/edit/delete/export/import
- Semantic search (vector similarity matching)
- One-click project data deletion
- Session status, issue tracking
- Tag management (rename, merge, batch delete)
- Token authentication protection
- 3D vector memory network visualization
- 🌐 Multi-language support (简体中文 / 繁體中文 / English / Español / Deutsch / Français / 日本語)

<p align="center">
  <img src="dashboard-projects.png" alt="Project Selection" width="100%">
  <br>
  <em>Project Selection</em>
</p>

<p align="center">
  <img src="dashboard-overview.png" alt="Overview & Vector Network Visualization" width="100%">
  <br>
  <em>Overview & Vector Network Visualization</em>
</p>

## ⚡ Shared Embedding Service

Multiple Memory Proxy workers share one Embedding model, avoiding redundant loading per process (200MB × N → 200MB × 1).

```bash
# Start Embedding shared service (default port 8900)
team-run embed-server
team-run embed-server --port 8900              # Specify port
team-run embed-server --port 8900 --daemon     # Run in background
team-run embed-server --bind 0.0.0.0           # Allow remote access
```

Memory Proxy connects to the shared service via `--embed-url`:

```bash
team-run memory-proxy \
  --pg-url "postgresql://..." \
  --embed-url "http://127.0.0.1:8900" \
  --workers 4
```

- With `--embed-url`, EmbeddingEngine auto-switches to remote mode, calling the shared service via HTTP
- Auto-fallback to local mode when the shared service is unavailable — zero disruption
- HTTP endpoints: `GET /health` (health check), `POST /encode` (single text encoding), `POST /encode_batch` (batch encoding)

## ⚡ Pairing with Steering Rules

GatewayAIVectorMemory is the storage layer. Use Steering rules to tell AI **when and how** to call these tools.

| IDE | Steering Location | Hooks |
|-----|------------------|-------|
| Kiro | `.kiro/steering/*.md` | `.kiro/hooks/*.hook` |
| Cursor | `.cursor/rules/*.md` | `.cursor/hooks.json` |
| Claude Code | `CLAUDE.md` (appended) | `.claude/settings.json` |
| Windsurf | `.windsurf/rules/*.md` | `.windsurf/hooks.json` |
| VSCode | `.github/copilot-instructions.md` (appended) | — |
| Trae | `.trae/rules/*.md` | — |
| OpenCode | `AGENTS.md` (appended) | `.opencode/plugins/*.js` |

## 🇨🇳 Users in China

The embedding model (~200MB) is auto-downloaded on first run. If slow:

```bash
export HF_ENDPOINT=https://hf-mirror.com
```

## 📦 Tech Stack

| Component | Technology |
|-----------|-----------|
| Runtime | Python >= 3.10 |
| Vector DB | PostgreSQL + pgvector |
| Embedding | ONNX Runtime + intfloat/multilingual-e5-small |
| Tokenizer | HuggingFace Tokenizers |
| HTTP API | FastAPI + Uvicorn |
| Web | FastAPI + Vanilla JS |

## 📋 Changelog

### v0.1.1

**PostgreSQL + HTTP Memory Proxy Architecture**
- 🔄 Storage backend migrated from SQLite + sqlite-vec to PostgreSQL + pgvector
- 🌐 New HTTP Memory Proxy (FastAPI + Uvicorn), replacing stdio MCP Server
- 👥 New team memory (team scope), one person's pitfall benefits all
- 🔐 Multi-user data isolation, Token / JWT / user mapping — three auth modes
- ⚡ Multi-worker support, shared Embedding service, memory drops 90%
- 📊 Web dashboard adapted for PostgreSQL, with Token auth and user filtering
- 🔌 All IDEs connect via HTTP API, no more stdio dependency

### v0.1.0

**Initial Release**
- ⚡ Shared Embedding service (`team-run embed-server`)
- 🧠 8 MCP tools: remember / recall / forget / status / track / task / readme / auto_save
- 📊 Web dashboard (3D vector network visualization)
- 🔍 Semantic search + smart dedup

## License

Apache-2.0
