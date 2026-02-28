# Memory Proxy：PostgreSQL + HTTP API + 用户隔离 + 团队共享记忆

## 背景

用户有一个 API Gateway 服务（100+ 用户，目标支持 1000 用户），需要在网关中集成记忆功能：请求转发前调 recall，响应完成后调 remember。

### 架构选型

| | 中间层 Memory Proxy | 直接改网关 |
|---|---|---|
| 改网关代码 | 不改 | 改（新增模块） |
| 部署复杂度 | 多一个服务 + Nginx 改路由 | 无额外服务 |
| 延迟 | 多一跳（localhost，影响小） | 无额外跳转 |
| 维护 | 三个项目独立更新 | 网关和记忆项目有耦合 |

选择 Memory Proxy 方案：不改网关代码，解耦独立维护。

## 目标

1. 独立 HTTP 服务作为中间层，Nginx 路由记忆相关请求，API Gateway 代码不改
2. PostgreSQL + pgvector 作为存储后端
3. user_id 维度隔离个人数据
4. team scope 共享团队记忆

## 架构

```
客户端 → Nginx → API Gateway → AI 后端
              ↘
          Memory Proxy (HTTP 服务)
              ↕
        PostgreSQL + pgvector
              ↕
        Embed Server (共享)
```

Nginx 路由规则：
- `/memory/*` → Memory Proxy（记忆相关请求）
- 其他 → API Gateway（正常业务请求）

Memory Proxy 是独立进程，与 API Gateway 无代码依赖。

## 应用场景

### 场景 1：团队共享开发服务器

```
服务器
├── Embed Server（单进程，200MB）
├── Memory Proxy (HTTP 服务)
│     ↕ PostgreSQL + pgvector
├── Nginx
│   ├── /memory/* → Memory Proxy
│   └── /* → API Gateway
├── API Gateway（不改代码）
│   ├── 用户 A1 请求
│   ├── 用户 A2 请求
│   └── 用户 A3 请求
└── PostgreSQL（共享）
```

API Gateway 集成方式（二选一）：
- 方式 A：Nginx 路由，Gateway 不改代码，前端/客户端直接请求 `/memory/*`
- 方式 B：Gateway 内部 HTTP 调用 Memory Proxy API（如需在转发前后自动 recall/remember）

记忆隔离：
- A1 用 `remember(scope="project")` → 只有 A1 能看到（project_dir + user_id）
- A1 用 `remember(scope="team")` → A1/A2/A3 都能看到（project_dir，无 user_id 过滤）
- A1 用 `auto_save` 存偏好 → 只有 A1 能看到（user_memories，user_id 隔离）
- A1 的 issues/tasks/session_state → 只有 A1 能看到（user_id 隔离）

### 场景 2：多团队多项目服务器

```
服务器
├── Embed Server
├── Memory Proxy (HTTP 服务)
│     ↕ PostgreSQL + pgvector
├── 团队 A（project-x）
│   ├── user_id=a1, project_dir=/srv/project-x
│   ├── user_id=a2, project_dir=/srv/project-x
│   └── user_id=a3, project_dir=/srv/project-x
├── 团队 B（project-y）
│   ├── user_id=b1, project_dir=/srv/project-y
│   └── user_id=b2, project_dir=/srv/project-y
└── PostgreSQL（共享）
```

隔离矩阵：
- a1 的 project 记忆 ≠ a2 的 project 记忆（user_id 不同）
- a1 的 team 记忆 = a2/a3 的 team 记忆（同 project_dir）
- a1 的 team 记忆 ≠ b1 的 team 记忆（project_dir 不同）
- a1 的 user_memories ≠ b1 的 user_memories（user_id 不同）

### 场景 3：Web 看板视角

```
team-run web --port 9080                    # 管理员：全部数据
team-run web --port 9080 --user-id a1      # 用户 a1：自己的数据 + 所属项目 team 记忆
```

---

## F1：PostgreSQL + pgvector 存储后端

### 需求描述

使用 PostgreSQL + pgvector 作为存储后端。

### 功能范围

1. PostgreSQL 表结构
   - `memories`：项目记忆，主键 `id TEXT`，向量列 `embedding vector(384)`
   - `user_memories`：用户记忆，主键 `id TEXT`，向量列 `embedding vector(384)`
   - `team_memories`：团队共享记忆，主键 `id TEXT`，向量列 `embedding vector(384)`
   - `session_state`：会话状态
   - `issues` / `issues_archive`：问题跟踪
   - `tasks` / `tasks_archive`：任务管理
   - `schema_version`：版本管理
2. 向量搜索
   - 使用 pgvector 的 `<=>` 余弦距离运算符
   - 向量列直接内嵌在业务表中
   - 可选：创建 IVFFlat 或 HNSW 索引加速搜索
3. 首次启动时自动创建表结构

### 验收标准

- [ ] PostgreSQL 表结构完整
- [ ] pgvector 向量搜索正常工作
- [ ] 首次启动自动建表

---

## F2：Memory Proxy HTTP 服务

### 需求描述

Memory Proxy HTTP 服务作为独立中间层运行。API Gateway 不改代码，通过 Nginx 路由或直接 HTTP 调用使用记忆功能。

### 功能范围

1. 启动命令
   ```
   team-run memory-proxy --port 8080 --bind 0.0.0.0 --pg-url postgresql://user:pass@localhost/teamai --embed-url http://localhost:8900
   ```
2. REST API 端点
   - `POST /memory/remember` → remember 工具
   - `POST /memory/recall` → recall 工具
   - `POST /memory/forget` → forget 工具
   - `POST /memory/status` → status 工具
   - `POST /memory/track` → track 工具
   - `POST /memory/task` → task 工具
   - `POST /memory/auto_save` → auto_save 工具
   - `GET /memory/health` → 健康检查
3. 请求格式
   - Content-Type: application/json
   - 请求体与现有工具的 arguments 一致
   - 必传 Header：`X-User-Id`（用户标识）、`X-Project-Dir`（项目目录）
4. 响应格式
   - 统一 JSON：`{"success": true/false, "data": {...}, "error": "..."}`
5. 并发模型
   - 使用 uvicorn + 多 worker 支撑并发
   - `--workers` 参数控制工作进程数，默认 4
   - PostgreSQL 连接池（每 worker 独立连接池）

### 验收标准

- [ ] `team-run memory-proxy` 启动 HTTP 服务
- [ ] 所有工具通过 REST API 可调用
- [ ] X-User-Id / X-Project-Dir Header 正确传递
- [ ] 健康检查端点正常
- [ ] 多 worker 并发处理请求

---

## F3：用户级数据隔离

### 需求描述

增加 `user_id` 维度，确保多用户共享服务器时个人数据互不可见。

### 功能范围

1. user_id 传入方式
   - `X-User-Id` Header（必传）
   - 启用 JWT 认证时：JWT payload 中的 `user_id` 优先于 Header（防伪造）
2. 数据库 schema
   - 所有表包含 `user_id TEXT NOT NULL` 列
   - `session_state` UNIQUE 约束为 `(project_dir, user_id)`
3. 数据访问层
   - 所有查询/写入增加 user_id 过滤
   - team_memories 写入时记录 `created_by`（user_id），但查询不按 user_id 过滤
4. session_id 按 `(project_dir, user_id)` 独立递增
5. Web 看板
   - 支持 `--user-id` 参数过滤
   - 不传时展示全部（管理员模式）

### 验收标准

- [ ] `X-User-Id` Header 正确传递
- [ ] 同 project_dir 不同 user_id 的数据互不可见
- [ ] session_id 按 (project_dir, user_id) 独立递增
- [ ] 看板按 user_id 过滤
- [ ] JWT 模式下 user_id 从 token 提取，优先于 Header

---

## F4：团队共享记忆（team scope）

### 需求描述

新增 `scope: "team"` 记忆层，同一 project_dir 下所有用户可见，用于共享踩坑经验、架构知识等团队级信息。

### 三层记忆体系

| scope | 存储表 | 隔离维度 | 用途 |
|-------|--------|----------|------|
| user | user_memories | user_id | 个人偏好，跨项目 |
| project | memories | project_dir + user_id | 个人项目记忆 |
| team | team_memories | project_dir | 团队共享记忆 |

### 存储时机与 scope 判断规则

| 内容类型 | scope | 说明 |
|----------|-------|------|
| 踩坑经验（通用价值） | team | 团队共享，同项目所有人可见 |
| 架构知识、项目约定 | team | 团队共享 |
| 个人排查过程、行为纠正 | project | 个人项目记忆，仅自己可见 |
| 个人偏好 | user（auto_save） | 跨项目，仅自己可见 |

判断原则：
- 默认 `project`（个人项目记忆）
- 只有明确具有团队共享价值的内容才写入 `team`
- `auto_save` 始终写入 `user` scope

### 功能范围

1. team_memories 表
   - 按 project_dir 隔离，不含 user_id 过滤
   - 写入时记录 `created_by`（user_id）
2. remember 工具扩展
   - `scope: "team"` 写入 team_memories 表
3. recall 工具扩展
   - `scope: "team"` 只搜索 team_memories
   - `scope: "all"` 同时搜索 memories + team_memories + user_memories，各表取 top_k 后合并，按相似度统一排序，取最终 top_k 条返回
   - `scope: "project"` 只搜索 memories
4. forget 工具扩展
   - 支持删除 team_memories 中的记忆
5. Web 看板
   - 记忆列表增加 scope 筛选（project / team / user）
   - team 记忆显示 created_by 标记

### 验收标准

- [ ] `remember(scope="team")` 写入 team_memories 表
- [ ] 同 project_dir 的所有 user_id 都能 recall 到 team 记忆
- [ ] 不同 project_dir 的 team 记忆互不可见
- [ ] `recall(scope="all")` 各表取 top_k 后合并排序，返回最终 top_k 条
- [ ] team 记忆记录 created_by 字段
- [ ] 看板支持 scope 筛选

---

## F5：配置管理

### 需求描述

统一管理配置，支持命令行参数和环境变量。

### 功能范围

1. 配置项
   - `--pg-url` / `TEAMAIVECTORMEMORY_PG_URL`：PostgreSQL 连接字符串（必传）
   - `--embed-url` / `TEAMAIVECTORMEMORY_EMBED_URL`：Embedding 服务地址（必传）
2. memory-proxy 子命令参数
   - `--port`：HTTP 端口，默认 8080
   - `--bind`：绑定地址，默认 0.0.0.0
   - `--token`：静态 token 认证
   - `--jwt-secret`：JWT 验签密钥（与 `--token` 互斥）
   - `--user-tokens`：token → user_id 映射文件（JSON 格式）
   - `--workers`：工作进程数，默认 4

### 验收标准

- [ ] 命令行参数和环境变量均可配置
- [ ] memory-proxy 子命令参数完整

---

## F6：Embed Server 复用

### 需求描述

Memory Proxy 复用现有的 `team-run embed-server`，通过 HTTP 调用 Embedding 服务。

### 功能范围

1. 已有实现
   - `team-run embed-server --port 8900` 已实现
   - `EmbeddingEngine` 已支持 `--embed-url` 远程模式
2. Memory Proxy 集成
   - memory-proxy 启动时必须指定 `--embed-url`
   - 健康检查包含 embed-server 连通性检测

### 验收标准

- [ ] memory-proxy 通过 embed-url 调用 Embedding 服务
- [ ] embed-server 不可用时 memory-proxy 健康检查报错

---

## F7：认证与鉴权

### 需求描述

Memory Proxy 和 Web 看板自带认证机制，防止未授权访问。

### 功能范围

1. 认证中间件（Memory Proxy + Web 看板共用）
   - 静态 token 模式：`--token` 参数，请求需带 `Authorization: Bearer <token>` Header
   - JWT 模式：`--jwt-secret` 验签，JWT payload 携带 `user_id` 和 `role`
   - 两种模式互斥
2. 角色区分
   - `admin`：可查看所有用户数据、所有项目数据
   - `user`：只能查看自己的数据 + 所属项目的 team 记忆
   - 静态 token 模式下：`--token` 为 admin 权限；`--user-tokens` 文件映射 token → user_id（JSON 格式：`{"token1": "user_id_1", "token2": "user_id_2"}`）
   - JWT 模式下：role 和 user_id 从 JWT payload 读取
3. Web 看板登录
   - 启用 token 时展示登录页，输入 token 后存 localStorage
   - 后续请求自动带 `Authorization: Bearer <token>` Header
   - 登出清除 localStorage
4. 安全默认值
   - 不启用 token 时：仅允许 `127.0.0.1` 访问
   - `--bind 0.0.0.0` 且未设认证时启动警告提示

### 验收标准

- [ ] 启用 token 后，无 token 请求返回 401
- [ ] 静态 token 正确认证
- [ ] JWT 验签正确，payload 中 user_id/role 正确提取
- [ ] admin 角色可查看全部数据
- [ ] user 角色只能查看自己的数据 + team 记忆
- [ ] Web 看板登录页正常工作
- [ ] 不启用认证 + bind 0.0.0.0 时仅允许 127.0.0.1 访问
- [ ] `--user-tokens` 支持 JSON 文件格式

---

## F8：清理旧代码

### 需求描述

删除 SQLite + stdio + IDE 单用户相关代码，项目只保留 PostgreSQL + HTTP 团队多用户模式。

### 功能范围

1. 删除 SQLite 相关
   - `teamaivectormemory/db/connection.py` 中 SQLite 连接逻辑
   - `teamaivectormemory/db/schema.py` 中 SQLite 建表和迁移逻辑
   - sqlite-vec 相关依赖
2. 删除 stdio MCP Server
   - `teamaivectormemory/server.py`（MCP stdio server）
   - `teamaivectormemory/protocol.py`（JSON-RPC 协议处理）
3. 删除 IDE MCP 安装器
   - `teamaivectormemory/install.py`（整个文件，含 STEERING_CONTENT、HOOKS_CONFIGS、各 IDE 配置写入逻辑）
   - `teamaivectormemory/hooks/` 目录（含 `check_track.sh`、`__init__.py`）
   - `__main__.py` 中 `install` 子命令
4. 修改 `__main__.py`
   - 删除默认 stdio 启动逻辑（当前无子命令时调用 `run_server()`）
   - 无子命令时改为打印帮助信息
   - 新增 `memory-proxy` 子命令（F2 实现）
5. 更新 `pyproject.toml`
   - 移除 `sqlite-vec>=0.1.0` 依赖
   - 新增 `psycopg[binary]`、`pgvector`、`uvicorn` 依赖
   - 更新 `description`（当前含"MCP Server"，改为团队记忆 HTTP 服务描述）
   - 更新 `keywords`（移除 `"mcp"`、`"sqlite"`，新增 `"postgresql"`、`"pgvector"`、`"http"`、`"team"`）
6. 更新 `tools/readme.py`
   - 移除 SQLite 相关描述（当前 `_generate_deps_section` 写死 "Vector DB | SQLite + sqlite-vec"）
   - 移除 "Protocol | Model Context Protocol (MCP)" 描述
   - 更新为 PostgreSQL + HTTP 技术栈描述
7. 更新文档
   - `README.md` + `docs/` 下 6 个多语言 README（`README.en.md`、`README.zh-TW.md`、`README.ja.md`、`README.de.md`、`README.fr.md`、`README.es.md`）
   - 当前内容描述 SQLite + stdio MCP Server 用法，需重写为 PostgreSQL + HTTP Memory Proxy 用法
8. 清理 `scripts/` 目录
   - 删除 stdio MCP 测试脚本：`test_mcp_connect.py`、`test_mcp_start.py`、`test_mcp_start2.py`、`test_mcp_stdio.py`、`debug_protocol.py`
   - 删除 IDE 安装相关：`fix_user_mcp.py`
   - 评估保留：`migrate_data.py`（可能需要改为 SQLite → PostgreSQL 迁移工具）、`start_dashboard.sh`、`test_embed_*.py`、`rename_*.py`、`test_import.py`

### 保留

- `team-run embed-server`（Embedding 服务）
- `team-run web`（Web 看板，改为连 PostgreSQL）
- 工具层代码（remember/recall/forget/status/track/task/auto_save）
- `tools/keywords.py`（关键词提取，与存储无关）

### 验收标准

- [ ] SQLite 相关代码已删除
- [ ] stdio MCP Server 代码已删除（`server.py`、`protocol.py`）
- [ ] IDE 安装器已删除（`install.py`、`hooks/` 目录）
- [ ] `__main__.py` 无子命令时打印帮助，不再启动 stdio server
- [ ] `pyproject.toml` 依赖更新（移除 sqlite-vec，新增 psycopg/pgvector/uvicorn）
- [ ] `pyproject.toml` 元数据更新（description、keywords）
- [ ] `tools/readme.py` 技术栈描述更新为 PostgreSQL + HTTP
- [ ] README 及多语言文档重写为 Memory Proxy 用法
- [ ] stdio 相关测试脚本已删除
- [ ] 项目只能通过 `team-run memory-proxy` / `team-run web` / `team-run embed-server` 启动

---

## 非功能需求

1. 性能
   - 多 worker 模式支持 1000 并发用户
   - 单次 recall 响应 < 200ms（含向量搜索）
   - PostgreSQL 行级锁，无全局写锁
   - 每 worker 独立 PostgreSQL 连接池
2. 可观测性
   - Memory Proxy 请求日志（user_id, project_dir, tool, latency）
   - 健康检查端点（含 PostgreSQL 连通性 + Embed Server 连通性）
3. 安全
   - 自带 token 或 JWT 认证
   - 不启用认证时仅允许 127.0.0.1 访问
   - JWT 模式下 user_id 从签名 token 中提取，防伪造

## 不在范围内

- IDE 单用户模式（由 aivectormemory 项目负责）
- 用户注册/管理界面（user_id 由外部传入或 JWT 携带）
- 数据加密（依赖 PostgreSQL 自身加密和网络 TLS）
- team 记忆的权限控制（如只读/读写）
- 异步 IO（通过多 worker 实现并发）
- 多 PostgreSQL 实例 / 读写分离
- OAuth / SSO 集成
- API Gateway 代码修改

## 验收标准（整体）

- [ ] `team-run memory-proxy --pg-url ... --embed-url ...` 启动 HTTP 服务
- [ ] Nginx 路由 `/memory/*` 到 Memory Proxy，API Gateway 不改代码
- [ ] 多用户数据按 user_id 隔离
- [ ] team scope 记忆在同 project_dir 用户间共享
- [ ] Web 看板支持 user_id 过滤和 scope 筛选
- [ ] 启用认证后未认证请求返回 401
- [ ] 不启用认证时仅允许本地访问
- [ ] 多 worker 并发支撑 1000 用户
- [ ] SQLite + stdio 代码已删除
