🌐 简体中文 | [繁體中文](docs/README.zh-TW.md) | [English](docs/README.en.md) | [Español](docs/README.es.md) | [Deutsch](docs/README.de.md) | [Français](docs/README.fr.md) | [日本語](docs/README.ja.md)

<p align="center">
  <h1 align="center">🧠 GatewayAIVectorMemory</h1>
  <p align="center">
    <strong>给 AI 编程助手装上团队记忆 — PostgreSQL + pgvector 存储 · HTTP Memory Proxy · 多人协作知识共享</strong>
  </p>
  <p align="center">
    <a href="https://pypi.org/project/gatewayaivectormemory/"><img src="https://img.shields.io/pypi/v/gatewayaivectormemory?color=blue&label=PyPI" alt="PyPI"></a>
    <a href="https://pypi.org/project/gatewayaivectormemory/"><img src="https://img.shields.io/pypi/pyversions/gatewayaivectormemory" alt="Python"></a>
    <a href="https://github.com/cmsyt/teamaivectormemory/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-Apache_2.0-green" alt="License"></a>
  </p>
</p>

---

> **你是否也有这样的困扰？** 每开一个新会话，AI 就像换了个人 — 昨天刚教会它的项目规范今天又忘了，踩过的坑还会再踩一遍，开发到一半的进度全部归零。团队里每个人都在重复踩同样的坑，知识无法沉淀，经验无法传承。
>
> **GatewayAIVectorMemory 是为团队打造的 AI 记忆中枢。** PostgreSQL + pgvector 存储，HTTP Memory Proxy 统一接入，团队踩坑经验自动共享，架构知识一人沉淀全员受益，多用户数据严格隔离互不干扰。支持多 worker 共享 Embedding 模型，N 个进程只需 1 份内存。新会话自动恢复上下文，语义搜索精准召回，Token 消耗直降 50%+。

## ✨ 核心特性

| 特性 | 说明 |
|------|------|
| 👥 **团队知识共享** | 一人踩坑全员受益 — 团队记忆自动共享，架构知识、踩坑经验沉淀为团队资产 |
| 🔐 **多用户数据隔离** | 同一台服务器多人协作，个人记忆严格隔离互不可见，团队记忆按项目共享 |
| ⚡ **Embedding 共享服务** | N 个 worker 共享一个 Embedding 模型，200MB × N → 200MB × 1，内存直降 90% |
| 🧠 **跨会话记忆** | 踩过的坑、做过的决策、定下的规范，换个会话照样记得 |
| 🔍 **语义搜索** | 搜"数据库超时"就能找到"连接池踩坑"，不用记原文怎么写 |
| 💰 **省 50%+ Token** | 语义检索按需召回，告别全量上下文注入 |
| 🔗 **任务驱动开发** | 问题追踪 → 任务拆分 → 状态同步 → 联动归档，AI 自动管理完整开发流程 |
| 📊 **Web 看板** | 可视化管理所有记忆和任务，3D 向量网络一眼看清知识关联 |
| 🔌 **全 IDE 通吃** | Cursor / Kiro / Claude Code / Windsurf / VSCode / OpenCode / Trae — 通过 HTTP API 接入 |
| 🔄 **智能去重** | 相似度 > 0.95 自动合并更新，记忆库永远干净 |

## 🏗️ 架构

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
│  │ Auth 中间件   │  │  X-User-Id / X-Project-Dir│ │
│  │ Token/JWT    │  │  多用户隔离               │ │
│  └──────────────┘  └───────────────────────────┘ │
└──────────┬───────────────────┬───────────────────┘
           │                   │
┌──────────▼──────────┐ ┌─────▼─────────────────┐
│  Embedding Server   │ │  PostgreSQL + pgvector │
│  (ONNX Runtime)     │ │  向量存储 + 全文检索    │
│  HTTP :8900         │ │  多表隔离              │
└─────────────────────┘ └───────────────────────┘
```

## 🚀 快速开始

### 前置条件

- Python >= 3.10
- PostgreSQL >= 14（需安装 pgvector 扩展）
- 安装 pgvector：`CREATE EXTENSION IF NOT EXISTS vector;`

### 安装

```bash
pip install gatewayaivectormemory
```

### 1. 启动 Embedding 共享服务

```bash
# 默认端口 8900
team-run embed-server

# 指定端口 + 后台运行
team-run embed-server --port 8900 --daemon

# 允许远程访问
team-run embed-server --bind 0.0.0.0 --port 8900
```

> 首次启动会自动下载 Embedding 模型（~200MB）。中国用户可设置 `export HF_ENDPOINT=https://hf-mirror.com` 加速。

### 2. 启动 Memory Proxy

```bash
team-run memory-proxy \
  --pg-url "postgresql://user:pass@localhost:5432/dbname" \
  --embed-url "http://127.0.0.1:8900" \
  --port 8080 \
  --workers 4
```

认证选项（三选一，互斥）：

```bash
# 静态 Token 认证
team-run memory-proxy --pg-url "..." --token "your-secret-token"

# JWT 认证
team-run memory-proxy --pg-url "..." --jwt-secret "your-jwt-secret"

# 用户 Token 映射文件
team-run memory-proxy --pg-url "..." --user-tokens "/path/to/tokens.json"
```

### 3. 配置 IDE

在 IDE 的 MCP 配置文件中添加：

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
<summary>📍 IDE 配置文件位置</summary>

| IDE | 配置路径 |
|-----|---------|
| Kiro | `.kiro/settings/mcp.json` |
| Cursor | `.cursor/mcp.json` |
| Claude Code | `.mcp.json` |
| Windsurf | `.windsurf/mcp.json` |
| VSCode | `.vscode/mcp.json` |
| Trae | `.trae/mcp.json` |
| OpenCode | `opencode.json` |

</details>

## 🛠️ 8 个 MCP 工具

### `remember` — 存入记忆

```
content    (string, 必填)    记忆内容，Markdown 格式
tags       (string[], 必填)  标签，如 ["踩坑", "python"]
scope      (string)          "project"(默认) / "user"(跨项目) / "team"(团队共享)
```

相似度 > 0.95 自动合并更新，不会产生重复。team scope 写入团队记忆表，同项目所有成员可见。

### `recall` — 语义搜索

```
query      (string)     语义搜索关键词
tags       (string[])   精确标签过滤
scope      (string)     "project" / "user" / "team" / "all"
top_k      (integer)    返回数量，默认 5
brief      (boolean)    精简模式，true 时只返回 content 和 tags
source     (string)     按来源过滤：manual / experience
```

向量相似度匹配 — 用词不同也能找到相关记忆。

### `forget` — 删除记忆

```
memory_id  (string)     单个 ID
memory_ids (string[])   批量 ID
tags       (string[])   按标签批量删除
scope      (string)     配合 tags 使用，限定删除范围
```

### `status` — 会话状态

```
state (object, 可选)    不传=读取，传=部分更新
  is_blocked, block_reason, current_task,
  next_step, recent_changes[], pending[]
clear_fields (string[]) 要清空的列表字段名
```

跨会话维护工作进度，新会话自动恢复上下文。`progress` 为只读计算字段，自动从 track + task 聚合。

### `track` — 问题追踪

```
action     (string)   "create" / "update" / "archive" / "delete" / "list"
title      (string)   问题标题
issue_id   (integer)  问题 ID
status     (string)   "pending" / "in_progress" / "completed"
content    (string)   问题描述
investigation (string) 排查过程
root_cause (string)   根本原因
solution   (string)   解决方案
files_changed (string) 修改文件清单（JSON 数组）
test_result (string)  自测结果
```

### `task` — 任务管理

```
action     (string, 必填)  "batch_create" / "update" / "list" / "delete" / "archive"
feature_id (string)        关联功能标识（list 时必填）
tasks      (array)         任务列表（batch_create，支持子任务）
task_id    (integer)       任务 ID（update）
status     (string)        "pending" / "in_progress" / "completed" / "skipped"
```

通过 feature_id 关联 spec 文档。update 自动同步 tasks.md checkbox 和关联 issue 状态。

### `readme` — README 生成

```
action     (string)    "generate"(默认) / "diff"(对比差异)
lang       (string)    语言：en / zh-TW / ja / de / fr / es
sections   (string[])  指定章节：header / tools / deps
```

从 TOOL_DEFINITIONS / pyproject.toml 自动生成 README 内容，支持多语言和差异对比。

### `auto_save` — 自动保存偏好

```
preferences  (string[])  用户表达的技术偏好（固定 scope=user，跨项目通用）
extra_tags   (string[])  额外标签
```

每次会话结束自动提取并存储用户偏好，智能去重。

## 📊 Web 看板

```bash
team-run web --pg-url "postgresql://user:pass@localhost:5432/dbname" --port 9080
team-run web --pg-url "..." --embed-url "http://127.0.0.1:8900" --port 9080
team-run web --pg-url "..." --port 9080 --quiet          # 屏蔽请求日志
team-run web --pg-url "..." --port 9080 --quiet --daemon  # 后台运行
team-run web --pg-url "..." --token "secret" --port 9080  # Token 认证保护
team-run web --pg-url "..." --user-id "alice" --port 9080 # 指定用户（不传=管理员模式）
```

浏览器访问 `http://localhost:9080`。

- 多项目切换，记忆浏览/搜索/编辑/删除/导出/导入
- 语义搜索（向量相似度匹配）
- 一键删除项目数据
- 会话状态、问题追踪
- 标签管理（重命名、合并、批量删除）
- Token 认证保护
- 3D 向量记忆网络可视化
- 🌐 多语言支持（简体中文 / 繁體中文 / English / Español / Deutsch / Français / 日本語）

<p align="center">
  <img src="docs/dashboard-projects.png" alt="项目选择" width="100%">
  <br>
  <em>项目选择</em>
</p>

<p align="center">
  <img src="docs/dashboard-overview.png" alt="总览 & 向量网络可视化" width="100%">
  <br>
  <em>总览 & 向量网络可视化</em>
</p>

## ⚡ Embedding 共享服务

多个 Memory Proxy worker 共享一个 Embedding 模型，避免每个进程重复加载（200MB × N → 200MB × 1）。

```bash
# 启动 Embedding 共享服务（默认端口 8900）
team-run embed-server
team-run embed-server --port 8900              # 指定端口
team-run embed-server --port 8900 --daemon     # 后台运行
team-run embed-server --bind 0.0.0.0           # 允许远程访问
```

Memory Proxy 通过 `--embed-url` 参数连接共享服务：

```bash
team-run memory-proxy \
  --pg-url "postgresql://..." \
  --embed-url "http://127.0.0.1:8900" \
  --workers 4
```

- 设置 `--embed-url` 后，EmbeddingEngine 自动切换为远程模式，通过 HTTP 调用共享服务
- 共享服务不可用时自动降级为本地模式 — 零中断
- HTTP 端点：`GET /health`（健康检查）、`POST /encode`（单文本编码）、`POST /encode_batch`（批量编码）

## ⚡ 搭配 Steering 规则

GatewayAIVectorMemory 是存储层。通过 Steering 规则告诉 AI **何时、如何**调用这些工具。

| IDE | Steering 位置 | Hooks |
|-----|--------------|-------|
| Kiro | `.kiro/steering/*.md` | `.kiro/hooks/*.hook` |
| Cursor | `.cursor/rules/*.md` | `.cursor/hooks.json` |
| Claude Code | `CLAUDE.md`（追加） | `.claude/settings.json` |
| Windsurf | `.windsurf/rules/*.md` | `.windsurf/hooks.json` |
| VSCode | `.github/copilot-instructions.md`（追加） | — |
| Trae | `.trae/rules/*.md` | — |
| OpenCode | `AGENTS.md`（追加） | `.opencode/plugins/*.js` |

<details>
<summary>📋 Steering 规则示例</summary>

```markdown
# GatewayAIVectorMemory - 工作规则

## 1. 新会话启动（按顺序执行）

1. `recall`（tags: ["项目知识"], scope: "project", top_k: 100）加载项目知识
2. `recall`（tags: ["preference"], scope: "user", top_k: 20）加载用户偏好
3. `status`（不传 state）读取会话状态
4. 有阻塞 → 汇报等待；无阻塞 → 进入处理流程

## 2. 消息处理流程

- 步骤 A：`status` 读取状态，有阻塞则等待
- 步骤 B：判断消息类型（闲聊/纠正/偏好/代码问题）
- 步骤 C：`track create` 记录问题
- 步骤 D：排查（`recall` 踩坑记录 + 查看代码 + 找根因）
- 步骤 E：向用户说明方案，设阻塞等确认
- 步骤 F：修改代码（修改前 `recall` 检查踩坑记录）
- 步骤 G：运行测试验证
- 步骤 H：设阻塞等待用户验证
- 步骤 I：用户确认 → `track archive` + 清除阻塞
```

</details>

## 🇨🇳 中国用户

Embedding 模型（~200MB）首次运行自动下载。如果速度慢：

```bash
export HF_ENDPOINT=https://hf-mirror.com
```

## 📦 技术栈

| 组件 | 技术 |
|------|------|
| Runtime | Python >= 3.10 |
| Vector DB | PostgreSQL + pgvector |
| Embedding | ONNX Runtime + intfloat/multilingual-e5-small |
| Tokenizer | HuggingFace Tokenizers |
| HTTP API | FastAPI + Uvicorn |
| Web | FastAPI + Vanilla JS |

## 📋 更新日志

### v0.1.1

**PostgreSQL + HTTP Memory Proxy 架构**
- 🔄 存储后端从 SQLite + sqlite-vec 迁移到 PostgreSQL + pgvector
- 🌐 新增 HTTP Memory Proxy（FastAPI + Uvicorn），替代 stdio MCP Server
- 👥 新增团队记忆（team scope），一人踩坑全员受益
- 🔐 多用户数据隔离，Token / JWT / 用户映射三种认证模式
- ⚡ 多 worker 支持，共享 Embedding 服务，内存直降 90%
- 📊 Web 看板适配 PostgreSQL，支持 Token 认证和用户过滤
- 🔌 全 IDE 通过 HTTP API 接入，不再依赖 stdio

### v0.1.0

**初始版本**
- ⚡ Embedding 共享服务（`team-run embed-server`）
- 🧠 8 个 MCP 工具：remember / recall / forget / status / track / task / readme / auto_save
- 📊 Web 看板（3D 向量网络可视化）
- 🔍 语义搜索 + 智能去重

## License

Apache-2.0
