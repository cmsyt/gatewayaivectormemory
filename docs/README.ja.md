🌐 [简体中文](../README.md) | [繁體中文](README.zh-TW.md) | [English](README.en.md) | [Español](README.es.md) | [Deutsch](README.de.md) | [Français](README.fr.md) | 日本語

<p align="center">
  <h1 align="center">🧠 GatewayAIVectorMemory</h1>
  <p align="center">
    <strong>AIコーディングアシスタントにチーム記憶を — PostgreSQL + pgvector ストレージ · HTTP Memory Proxy · マルチユーザー協業ナレッジ共有</strong>
  </p>
  <p align="center">
    <a href="https://pypi.org/project/gatewayaivectormemory/"><img src="https://img.shields.io/pypi/v/gatewayaivectormemory?color=blue&label=PyPI" alt="PyPI"></a>
    <a href="https://pypi.org/project/gatewayaivectormemory/"><img src="https://img.shields.io/pypi/pyversions/gatewayaivectormemory" alt="Python"></a>
    <a href="https://github.com/cmsyt/gatewayaivectormemory/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-Apache_2.0-green" alt="License"></a>
  </p>
</p>

---

> **こんな経験ありませんか？** 新しいセッションを開くたびに、AIはまるで別人 — 昨日教えたプロジェクト規約は今日もう忘れている、踏んだ地雷をまた踏む、途中まで進めた作業はゼロに戻る。チーム全員が同じ地雷を繰り返し踏み、知識は蓄積されず、経験は継承されない。
>
> **GatewayAIVectorMemory はチームのために作られたAI記憶ハブです。** PostgreSQL + pgvector ストレージ、HTTP Memory Proxy で統一アクセス、チームの失敗経験は自動共有、アーキテクチャ知識は一人が蓄積すれば全員が恩恵を受けます。マルチユーザーデータは厳密に分離され相互干渉ゼロ。複数workerでEmbeddingモデルを共有可能：Nプロセスでメモリは1コピーのみ。新セッションは自動的にコンテキストを復元、セマンティック検索で的確に呼び出し、トークン消費を50%+削減。

## ✨ 主な機能

| 機能 | 説明 |
|------|------|
| 👥 **チームナレッジ共有** | 一人の失敗が全員の教訓に — チーム記憶は自動共有、アーキテクチャ知識や失敗経験がチーム資産として蓄積 |
| 🔐 **マルチユーザーデータ分離** | 同一サーバーで複数人が協業、個人記憶は厳密に分離され互いに不可視、チーム記憶はプロジェクト単位で共有 |
| ⚡ **Embedding共有サービス** | N個のworkerが1つのEmbeddingモデルを共有、200MB × N → 200MB × 1、メモリ消費を90%削減 |
| 🧠 **クロスセッション記憶** | 踏んだ地雷、下した決定、決めた規約、セッションが変わっても忘れない |
| 🔍 **セマンティック検索** |「データベースタイムアウト」で検索すれば「コネクションプール問題」が見つかる — 原文を覚えていなくてOK |
| 💰 **50%+トークン節約** | セマンティック検索でオンデマンド呼び出し、一括コンテキスト注入とはお別れ |
| 🔗 **タスク駆動開発** | 問題追跡 → タスク分割 → ステータス同期 → 連動アーカイブ。AIが開発フロー全体を自動管理 |
| 📊 **Webダッシュボード** | すべての記憶とタスクを視覚的に管理、3Dベクトルネットワークで知識の繋がりが一目瞭然 |
| 🔌 **全IDE対応** | Cursor / Kiro / Claude Code / Windsurf / VSCode / OpenCode / Trae — HTTP API で接続 |
| 🔄 **スマート重複排除** | 類似度 > 0.95 で自動マージ更新、記憶ストアは常にクリーン |

## 🏗️ アーキテクチャ

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
│  │ Token/JWT    │  │  マルチユーザー分離        │ │
│  └──────────────┘  └───────────────────────────┘ │
└──────────┬───────────────────┬───────────────────┘
           │                   │
┌──────────▼──────────┐ ┌─────▼─────────────────┐
│  Embedding Server   │ │  PostgreSQL + pgvector │
│  (ONNX Runtime)     │ │  ベクトルストレージ +   │
│  HTTP :8900         │ │  全文検索              │
└─────────────────────┘ └───────────────────────┘
```

## 🚀 クイックスタート

### 前提条件

- Python >= 3.10
- PostgreSQL >= 14（pgvector 拡張が必要）
- pgvector のインストール：`CREATE EXTENSION IF NOT EXISTS vector;`

### インストール

```bash
pip install gatewayaivectormemory
```

### 1. Embedding共有サービスを起動

```bash
# デフォルトポート 8900
team-run embed-server

# ポート指定 + バックグラウンド実行
team-run embed-server --port 8900 --daemon

# リモートアクセスを許可
team-run embed-server --bind 0.0.0.0 --port 8900
```

> 初回起動時にEmbeddingモデル（約200MB）が自動ダウンロードされます。中国のユーザーは `export HF_ENDPOINT=https://hf-mirror.com` で高速化できます。

### 2. Memory Proxy を起動

```bash
team-run memory-proxy \
  --pg-url "postgresql://user:pass@localhost:5432/dbname" \
  --embed-url "http://127.0.0.1:8900" \
  --port 8080 \
  --workers 4
```

認証オプション（排他的、いずれか1つ）：

```bash
# 静的Token認証
team-run memory-proxy --pg-url "..." --token "your-secret-token"

# JWT認証
team-run memory-proxy --pg-url "..." --jwt-secret "your-jwt-secret"

# ユーザーTokenマッピングファイル
team-run memory-proxy --pg-url "..." --user-tokens "/path/to/tokens.json"
```

### 3. IDE を設定

IDEのMCP設定ファイルに追加：

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
<summary>📍 各IDE設定ファイルの場所</summary>

| IDE | 設定ファイルパス |
|-----|----------------|
| Kiro | `.kiro/settings/mcp.json` |
| Cursor | `.cursor/mcp.json` |
| Claude Code | `.mcp.json` |
| Windsurf | `.windsurf/mcp.json` |
| VSCode | `.vscode/mcp.json` |
| Trae | `.trae/mcp.json` |
| OpenCode | `opencode.json` |

</details>

## 📊 Webダッシュボード

```bash
team-run web --pg-url "postgresql://user:pass@localhost:5432/dbname" --port 9080
team-run web --pg-url "..." --embed-url "http://127.0.0.1:8900" --port 9080
team-run web --pg-url "..." --port 9080 --quiet          # リクエストログを非表示
team-run web --pg-url "..." --port 9080 --quiet --daemon  # バックグラウンド実行
team-run web --pg-url "..." --token "secret" --port 9080  # Token認証保護
team-run web --pg-url "..." --user-id "alice" --port 9080 # ユーザー指定（省略=管理者モード）
```

ブラウザで `http://localhost:9080` にアクセス。

- マルチプロジェクト切り替え、記憶の閲覧/検索/編集/削除/エクスポート/インポート
- セマンティック検索（ベクトル類似度マッチング）
- プロジェクトデータのワンクリック削除
- セッション状態、問題追跡
- タグ管理（名前変更、統合、一括削除）
- Token認証保護
- 3Dベクトル記憶ネットワーク可視化
- 🌐 多言語対応（简体中文 / 繁體中文 / English / Español / Deutsch / Français / 日本語）

<p align="center">
  <img src="dashboard-projects.png" alt="プロジェクト選択" width="100%">
  <br>
  <em>プロジェクト選択</em>
</p>

<p align="center">
  <img src="dashboard-overview.png" alt="統計概要 & ベクトルネットワーク可視化" width="100%">
  <br>
  <em>統計概要 & ベクトルネットワーク可視化</em>
</p>

## ⚡ Embedding共有サービス

複数のMemory Proxy workerが1つのEmbeddingモデルを共有し、プロセスごとの重複ロードを回避します（200MB × N → 200MB × 1）。

```bash
# Embedding共有サービスを起動（デフォルトポート 8900）
team-run embed-server
team-run embed-server --port 8900              # ポート指定
team-run embed-server --port 8900 --daemon     # バックグラウンド実行
team-run embed-server --bind 0.0.0.0           # リモートアクセスを許可
```

Memory Proxy は `--embed-url` パラメータで共有サービスに接続：

```bash
team-run memory-proxy \
  --pg-url "postgresql://..." \
  --embed-url "http://127.0.0.1:8900" \
  --workers 4
```

- `--embed-url` を設定すると、EmbeddingEngineは自動的にリモートモードに切り替わり、HTTP経由で共有サービスを呼び出します
- 共有サービスが利用不可の場合、自動的にローカルモードにフォールバック — 影響ゼロ
- HTTPエンドポイント：`GET /health`（ヘルスチェック）、`POST /encode`（単一テキストエンコード）、`POST /encode_batch`（バッチエンコード）

## ⚡ Steeringルールとの組み合わせ

GatewayAIVectorMemory はストレージ層です。Steeringルールを使ってAIに**いつ、どのように**ツールを呼び出すかを指示します。

| IDE | Steeringの場所 | Hooks |
|-----|---------------|-------|
| Kiro | `.kiro/steering/*.md` | `.kiro/hooks/*.hook` |
| Cursor | `.cursor/rules/*.md` | `.cursor/hooks.json` |
| Claude Code | `CLAUDE.md`（追記） | `.claude/settings.json` |
| Windsurf | `.windsurf/rules/*.md` | `.windsurf/hooks.json` |
| VSCode | `.github/copilot-instructions.md`（追記） | — |
| Trae | `.trae/rules/*.md` | — |
| OpenCode | `AGENTS.md`（追記） | `.opencode/plugins/*.js` |

## 🇨🇳 中国のユーザー

Embeddingモデル（約200MB）は初回実行時に自動ダウンロードされます。遅い場合：

```bash
export HF_ENDPOINT=https://hf-mirror.com
```

## 📦 技術スタック

| コンポーネント | 技術 |
|---------------|------|
| ランタイム | Python >= 3.10 |
| ベクトルDB | PostgreSQL + pgvector |
| Embedding | ONNX Runtime + intfloat/multilingual-e5-small |
| トークナイザー | HuggingFace Tokenizers |
| HTTP API | FastAPI + Uvicorn |
| Web | FastAPI + Vanilla JS |

## 📋 更新履歴

### v0.1.1

**PostgreSQL + HTTP Memory Proxy アーキテクチャ**
- 🔄 ストレージバックエンドを SQLite + sqlite-vec から PostgreSQL + pgvector に移行
- 🌐 新しい HTTP Memory Proxy（FastAPI + Uvicorn）、stdio MCP Server を置き換え
- 👥 新しいチーム記憶（team scope）、一人の失敗が全員の教訓に
- 🔐 マルチユーザーデータ分離、Token / JWT / ユーザーマッピング — 3つの認証モード
- ⚡ マルチworker対応、Embedding共有サービス、メモリ消費90%削減
- 📊 WebダッシュボードがPostgreSQLに対応、Token認証とユーザーフィルタリング
- 🔌 全IDEがHTTP APIで接続、stdio依存を解消

### v0.1.0

**初回リリース**
- ⚡ Embedding共有サービス（`team-run embed-server`）
- 🧠 8つのMCPツール：remember / recall / forget / status / track / task / readme / auto_save
- 📊 Webダッシュボード（3Dベクトルネットワーク可視化）
- 🔍 セマンティック検索 + スマート重複排除

## License

Apache-2.0
