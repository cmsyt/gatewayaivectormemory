🌐 [简体中文](../README.md) | 繁體中文 | [English](README.en.md) | [Español](README.es.md) | [Deutsch](README.de.md) | [Français](README.fr.md) | [日本語](README.ja.md)

<p align="center">
  <h1 align="center">🧠 GatewayAIVectorMemory</h1>
  <p align="center">
    <strong>為 AI 程式助手裝上團隊記憶 — PostgreSQL + pgvector 儲存 · HTTP Memory Proxy · 多人協作知識共享</strong>
  </p>
  <p align="center">
    <a href="https://pypi.org/project/gatewayaivectormemory/"><img src="https://img.shields.io/pypi/v/gatewayaivectormemory?color=blue&label=PyPI" alt="PyPI"></a>
    <a href="https://pypi.org/project/gatewayaivectormemory/"><img src="https://img.shields.io/pypi/pyversions/gatewayaivectormemory" alt="Python"></a>
    <a href="https://github.com/cmsyt/gatewayaivectormemory/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-Apache_2.0-green" alt="License"></a>
  </p>
</p>

---

> **你是否也有這樣的困擾？** 每開一個新會話，AI 就像換了個人 — 昨天剛教會它的專案規範今天又忘了，踩過的坑還會再踩一遍，開發到一半的進度全部歸零。團隊裡每個人都在重複踩同樣的坑，知識無法沉澱，經驗無法傳承。
>
> **GatewayAIVectorMemory 是為團隊打造的 AI 記憶中樞。** PostgreSQL + pgvector 儲存，HTTP Memory Proxy 統一接入，團隊踩坑經驗自動共享，架構知識一人沉澱全員受益，多用戶資料嚴格隔離互不干擾。支援多 worker 共享 Embedding 模型，N 個進程只需 1 份記憶體。新會話自動恢復上下文，語義搜尋精準召回，Token 消耗直降 50%+。

## ✨ 核心特性

| 特性 | 說明 |
|------|------|
| 👥 **團隊知識共享** | 一人踩坑全員受益 — 團隊記憶自動共享，架構知識、踩坑經驗沉澱為團隊資產 |
| 🔐 **多用戶資料隔離** | 同一台伺服器多人協作，個人記憶嚴格隔離互不可見，團隊記憶按專案共享 |
| ⚡ **Embedding 共享服務** | N 個 worker 共享一個 Embedding 模型，200MB × N → 200MB × 1，記憶體直降 90% |
| 🧠 **跨會話記憶** | 踩過的坑、做過的決策、定下的規範，換個會話照樣記得 |
| 🔍 **語義搜尋** | 搜「資料庫逾時」就能找到「連線池踩坑」，不用記原文怎麼寫 |
| 💰 **省 50%+ Token** | 語義檢索按需召回，告別全量上下文注入 |
| 🔗 **任務驅動開發** | 問題追蹤 → 任務拆分 → 狀態同步 → 聯動歸檔，AI 自動管理完整開發流程 |
| 📊 **Web 看板** | 視覺化管理所有記憶和任務，3D 向量網路一眼看清知識關聯 |
| 🔌 **全 IDE 通吃** | Cursor / Kiro / Claude Code / Windsurf / VSCode / OpenCode / Trae — 透過 HTTP API 接入 |
| 🔄 **智慧去重** | 相似度 > 0.95 自動合併更新，記憶庫永遠乾淨 |

## 🏗️ 架構

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
│  │ Auth 中介層   │  │  X-User-Id / X-Project-Dir│ │
│  │ Token/JWT    │  │  多用戶隔離               │ │
│  └──────────────┘  └───────────────────────────┘ │
└──────────┬───────────────────┬───────────────────┘
           │                   │
┌──────────▼──────────┐ ┌─────▼─────────────────┐
│  Embedding Server   │ │  PostgreSQL + pgvector │
│  (ONNX Runtime)     │ │  向量儲存 + 全文檢索    │
│  HTTP :8900         │ │  多表隔離              │
└─────────────────────┘ └───────────────────────┘
```

## 🚀 快速開始

### 前置條件

- Python >= 3.10
- PostgreSQL >= 14（需安裝 pgvector 擴充）
- 安裝 pgvector：`CREATE EXTENSION IF NOT EXISTS vector;`

### 安裝

```bash
pip install gatewayaivectormemory
```

### 1. 啟動 Embedding 共享服務

```bash
# 預設端口 8900
team-run embed-server

# 指定端口 + 背景執行
team-run embed-server --port 8900 --daemon

# 允許遠端存取
team-run embed-server --bind 0.0.0.0 --port 8900
```

> 首次啟動會自動下載 Embedding 模型（~200MB）。中國用戶可設定 `export HF_ENDPOINT=https://hf-mirror.com` 加速。

### 2. 啟動 Memory Proxy

```bash
team-run memory-proxy \
  --pg-url "postgresql://user:pass@localhost:5432/dbname" \
  --embed-url "http://127.0.0.1:8900" \
  --port 8080 \
  --workers 4
```

認證選項（三選一，互斥）：

```bash
# 靜態 Token 認證
team-run memory-proxy --pg-url "..." --token "your-secret-token"

# JWT 認證
team-run memory-proxy --pg-url "..." --jwt-secret "your-jwt-secret"

# 用戶 Token 對映檔案
team-run memory-proxy --pg-url "..." --user-tokens "/path/to/tokens.json"
```

### 3. 設定 IDE

在 IDE 的 MCP 設定檔中新增：

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
<summary>📍 各 IDE 設定檔位置</summary>

| IDE | 設定檔路徑 |
|-----|------------|
| Kiro | `.kiro/settings/mcp.json` |
| Cursor | `.cursor/mcp.json` |
| Claude Code | `.mcp.json` |
| Windsurf | `.windsurf/mcp.json` |
| VSCode | `.vscode/mcp.json` |
| Trae | `.trae/mcp.json` |
| OpenCode | `opencode.json` |

</details>

## 📊 Web 看板

```bash
team-run web --pg-url "postgresql://user:pass@localhost:5432/dbname" --port 9080
team-run web --pg-url "..." --embed-url "http://127.0.0.1:8900" --port 9080
team-run web --pg-url "..." --port 9080 --quiet          # 屏蔽請求日誌
team-run web --pg-url "..." --port 9080 --quiet --daemon  # 背景執行
team-run web --pg-url "..." --token "secret" --port 9080  # Token 認證保護
team-run web --pg-url "..." --user-id "alice" --port 9080 # 指定用戶（不傳=管理員模式）
```

瀏覽器存取 `http://localhost:9080`。

- 多專案切換，記憶瀏覽/搜尋/編輯/刪除/匯出/匯入
- 語義搜尋（向量相似度匹配）
- 一鍵刪除專案資料
- 會話狀態、問題追蹤
- 標籤管理（重新命名、合併、批次刪除）
- Token 認證保護
- 3D 向量記憶網路視覺化
- 🌐 多語言支援（简体中文 / 繁體中文 / English / Español / Deutsch / Français / 日本語）

<p align="center">
  <img src="dashboard-projects.png" alt="專案選擇" width="100%">
  <br>
  <em>專案選擇</em>
</p>

<p align="center">
  <img src="dashboard-overview.png" alt="統計概覽 & 向量網路視覺化" width="100%">
  <br>
  <em>統計概覽 & 向量網路視覺化</em>
</p>

## ⚡ Embedding 共享服務

多個 Memory Proxy worker 共享一個 Embedding 模型，避免每個進程重複載入（200MB × N → 200MB × 1）。

```bash
# 啟動 Embedding 共享服務（預設端口 8900）
team-run embed-server
team-run embed-server --port 8900              # 指定端口
team-run embed-server --port 8900 --daemon     # 背景執行
team-run embed-server --bind 0.0.0.0           # 允許遠端存取
```

Memory Proxy 透過 `--embed-url` 參數連接共享服務：

```bash
team-run memory-proxy \
  --pg-url "postgresql://..." \
  --embed-url "http://127.0.0.1:8900" \
  --workers 4
```

- 設定 `--embed-url` 後，EmbeddingEngine 自動切換為遠端模式，透過 HTTP 呼叫共享服務
- 共享服務不可用時自動降級為本地模式 — 零中斷
- HTTP 端點：`GET /health`（健康檢查）、`POST /encode`（單文本編碼）、`POST /encode_batch`（批次編碼）

## ⚡ 搭配 Steering 規則

GatewayAIVectorMemory 是儲存層。透過 Steering 規則告訴 AI **何時、如何**呼叫這些工具。

| IDE | Steering 位置 | Hooks |
|-----|--------------|-------|
| Kiro | `.kiro/steering/*.md` | `.kiro/hooks/*.hook` |
| Cursor | `.cursor/rules/*.md` | `.cursor/hooks.json` |
| Claude Code | `CLAUDE.md`（追加） | `.claude/settings.json` |
| Windsurf | `.windsurf/rules/*.md` | `.windsurf/hooks.json` |
| VSCode | `.github/copilot-instructions.md`（追加） | — |
| Trae | `.trae/rules/*.md` | — |
| OpenCode | `AGENTS.md`（追加） | `.opencode/plugins/*.js` |

## 🇨🇳 中國用戶

Embedding 模型（~200MB）首次執行自動下載。如果速度慢：

```bash
export HF_ENDPOINT=https://hf-mirror.com
```

## 📦 技術棧

| 元件 | 技術 |
|------|------|
| 執行環境 | Python >= 3.10 |
| 向量資料庫 | PostgreSQL + pgvector |
| Embedding | ONNX Runtime + intfloat/multilingual-e5-small |
| 分詞器 | HuggingFace Tokenizers |
| HTTP API | FastAPI + Uvicorn |
| Web | FastAPI + Vanilla JS |

## 📋 更新日誌

### v0.1.1

**PostgreSQL + HTTP Memory Proxy 架構**
- 🔄 儲存後端從 SQLite + sqlite-vec 遷移到 PostgreSQL + pgvector
- 🌐 新增 HTTP Memory Proxy（FastAPI + Uvicorn），取代 stdio MCP Server
- 👥 新增團隊記憶（team scope），一人踩坑全員受益
- 🔐 多用戶資料隔離，Token / JWT / 用戶對映三種認證模式
- ⚡ 多 worker 支援，共享 Embedding 服務，記憶體直降 90%
- 📊 Web 看板適配 PostgreSQL，支援 Token 認證和用戶過濾
- 🔌 全 IDE 透過 HTTP API 接入，不再依賴 stdio

### v0.1.0

**初始版本**
- ⚡ Embedding 共享服務（`team-run embed-server`）
- 🧠 8 個 MCP 工具：remember / recall / forget / status / track / task / readme / auto_save
- 📊 Web 看板（3D 向量網路視覺化）
- 🔍 語義搜尋 + 智慧去重

## License

Apache-2.0
