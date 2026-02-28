# 需求文档：Embedding 共享服务

## 背景

用户将 teamaivectormemory 集成到 API Gateway 服务器部署，团队成员在本地通过网关连接。多个 MCP worker 进程各自独立加载 ~200MB 的 ONNX embedding 模型，N 个 worker = N × 200MB 内存，对服务器资源浪费严重。

## 应用场景

### 场景 1：个人开发者本地使用（现状，不受影响）

```
开发者笔记本
├── IDE (Kiro/Cursor/Claude Code)
│   └── MCP Worker（进程内加载模型，本地 SQLite）
└── ~/.teamaivectormemory/memory.db
```

- 单用户单进程，不需要 embed-server
- 本次改动对此场景零影响

### 场景 2：API Gateway 多 worker 部署

```
服务器
├── Embed Server（单进程，200MB）
├── Gateway / Load Balancer
│   ├── Worker-1  EMBEDDING_SERVER_URL=http://127.0.0.1:8900
│   ├── Worker-2  EMBEDDING_SERVER_URL=http://127.0.0.1:8900
│   └── Worker-N  ...
└── ~/.teamaivectormemory/memory.db

团队成员本地
├── IDE → cc switch → API Gateway → Worker → Embed Server
```

- N 个 worker 共享一个 embed-server，不各自加载模型
- N × 200MB → 1 × 200MB

### 场景 3：embed-server 独立部署

```
team-run embed-server --port 8900 --bind 0.0.0.0
EMBEDDING_SERVER_URL=http://embed-host:8900 team-run --project-dir ...
```

- 无状态，只做文本→向量转换，不碰数据库
- 支持 `/health` 健康检查
- embed-server 可以和 MCP worker 不在同一台机器

---

## 功能范围

### 1. 新增 `team-run embed-server` 子命令

- 暴露 `/encode`、`/encode_batch`、`/health` 接口
- 支持 `--port`（默认 8900）、`--bind`（默认 127.0.0.1）、`--daemon`

### 2. `EmbeddingEngine` 双模式

- 本地模式（默认）：行为不变，进程内加载 ONNX 模型
- 远程模式：检测到 `EMBEDDING_SERVER_URL` 环境变量时走 HTTP，不加载本地模型

### 3. 远程模式容错

- embed-server 不可用时自动降级到本地模式并打印警告
- HTTP 超时 10 秒，连接失败重试 1 次

### 4. 为后续功能预留扩展点

> 后续将实现用户级数据隔离（user_id）和团队共享记忆（team scope），本次开发需注意：
> - `EmbeddingEngine` 接口保持无状态，不绑定 user_id / scope 等业务概念
> - embed-server HTTP 接口只做文本→向量转换，不涉及数据库操作
> - `ConnectionManager` 和 Repo 层暂不改动，但代码结构保持可扩展（后续加 user_id 参数）

---

## 验收标准

- [ ] `team-run embed-server --port 8900` 启动，`/encode` 返回 384 维向量
- [ ] `--bind 0.0.0.0` 支持绑定地址
- [ ] `/encode_batch` 批量编码
- [ ] `/health` 返回模型状态
- [ ] 设置 `EMBEDDING_SERVER_URL` 后 worker 走 HTTP，不加载本地模型
- [ ] 不设置时行为不变（本地模式）
- [ ] embed-server 不可用时自动降级 + 警告日志
- [ ] `--daemon` 后台运行

---

## 不在范围内

- 用户级数据隔离（user_id）→ 见 `.kiro/specs/user-isolation-and-team-memory/`
- 团队共享记忆（team scope）→ 见 `.kiro/specs/user-isolation-and-team-memory/`
- 用户认证/鉴权（由网关层负责）
- embedding 模型切换/自定义模型
