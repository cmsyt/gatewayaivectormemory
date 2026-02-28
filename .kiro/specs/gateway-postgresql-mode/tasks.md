# Memory Proxy：PostgreSQL + HTTP API + 用户隔离 + 团队共享记忆 - 任务文档

## 第 1 组：F8 清理旧代码（先清后建，避免新旧混杂）

- [x] 1.1 删除 stdio MCP Server 代码
  - [x] 1.1.1 删除 `teamaivectormemory/server.py`
  - [x] 1.1.2 删除 `teamaivectormemory/protocol.py`
- [x] 1.2 删除 IDE 安装器
  - [x] 1.2.1 删除 `teamaivectormemory/install.py`
  - [x] 1.2.2 删除 `teamaivectormemory/hooks/` 目录（含 `check_track.sh`、`__init__.py`）
- [x] 1.3 删除 stdio 相关测试脚本
  - [x] 1.3.1 删除 `scripts/test_mcp_connect.py`、`scripts/test_mcp_start.py`、`scripts/test_mcp_start2.py`、`scripts/test_mcp_stdio.py`、`scripts/debug_protocol.py`
  - [x] 1.3.2 删除 `scripts/fix_user_mcp.py`
- [x] 1.4 修改 `teamaivectormemory/__main__.py`
  - [x] 1.4.1 删除 `install` 子命令及其 import
  - [x] 1.4.2 删除默认 stdio 启动逻辑（`else` 分支中的 `run_server()`），改为无子命令时打印帮助信息（`parser.print_help()`）
- [x] 1.5 清理 `teamaivectormemory/db/__init__.py` 中对已删除模块的引用（如有）
- [x] 1.6 运行 `python -c "from teamaivectormemory import __main__"` 验证 import 无报错

## 第 2 组：F1 PostgreSQL + pgvector 存储后端

- [x] 2.1 更新 `pyproject.toml`
  - [x] 2.1.1 移除 `sqlite-vec>=0.1.0` 依赖
  - [x] 2.1.2 新增依赖：`psycopg[binary]>=3.1`、`pgvector>=0.3`、`uvicorn>=0.30`、`fastapi>=0.110`
  - [x] 2.1.3 更新 `description` 为团队记忆 HTTP 服务描述（移除 "MCP Server"）
  - [x] 2.1.4 更新 `keywords`：移除 `"mcp"`、`"sqlite"`，新增 `"postgresql"`、`"pgvector"`、`"http"`、`"team"`
- [x] 2.2 重写 `teamaivectormemory/config.py`
  - [x] 2.2.1 移除 SQLite 相关配置（`DB_DIR`、`DB_NAME`、`get_db_path`、`OLD_DB_DIR`）
  - [x] 2.2.2 新增 PostgreSQL 配置项：`PG_URL`（环境变量 `TEAMAIVECTORMEMORY_PG_URL`）、`EMBED_URL`（环境变量 `TEAMAIVECTORMEMORY_EMBED_URL`）
  - [x] 2.2.3 保留 `MODEL_DIMENSION`、`DEDUP_THRESHOLD`、`DEFAULT_TOP_K` 等通用常量
- [x] 2.3 重写 `teamaivectormemory/db/connection.py`
  - [x] 2.3.1 移除 SQLite + sqlite-vec 连接逻辑
  - [x] 2.3.2 实现 `ConnectionManager`：接收 `pg_url` 参数，使用 `psycopg` 连接 PostgreSQL，支持连接池
  - [x] 2.3.3 `ConnectionManager` 增加 `project_dir`、`user_id` 属性
- [x] 2.4 重写 `teamaivectormemory/db/schema.py`
  - [x] 2.4.1 移除全部 SQLite 建表和迁移逻辑
  - [x] 2.4.2 PostgreSQL 建表 DDL：`memories`（含 `user_id TEXT NOT NULL`、`embedding vector(384)`）、`user_memories`（含 `user_id TEXT NOT NULL`、`embedding vector(384)`）、`team_memories`（含 `project_dir`、`created_by`、`embedding vector(384)`）、`session_state`（UNIQUE `(project_dir, user_id)`）、`issues`/`issues_archive`（含 `user_id`）、`tasks`/`tasks_archive`（含 `user_id`）、`schema_version`
  - [x] 2.4.3 实现 `init_db(conn)` 函数：启用 pgvector 扩展（`CREATE EXTENSION IF NOT EXISTS vector`）、创建表、创建索引
  - [x] 2.4.4 所有表增加 `user_id TEXT NOT NULL` 列（team_memories 用 `created_by` 代替）
- [x] 2.5 重写 `teamaivectormemory/db/memory_repo.py`
  - [x] 2.5.1 将 SQLite `vec_memories` 虚拟表查询改为 pgvector `<=>` 余弦距离查询
  - [x] 2.5.2 向量数据直接存储在 `memories` 表的 `embedding` 列，移除独立的 `vec_memories` 表
  - [x] 2.5.3 所有查询/写入增加 `user_id` 参数过滤
  - [x] 2.5.4 `insert`/`update`/`find_duplicate`/`search_by_vector`/`search_by_vector_with_tags` 适配 PostgreSQL 语法
- [x] 2.6 重写 `teamaivectormemory/db/user_memory_repo.py`
  - [x] 2.6.1 同 2.5，向量内嵌、pgvector 查询、增加 `user_id` 过滤
- [x] 2.7 新建 `teamaivectormemory/db/team_memory_repo.py`
  - [x] 2.7.1 实现 `TeamMemoryRepo`：操作 `team_memories` 表，按 `project_dir` 隔离，写入时记录 `created_by`
  - [x] 2.7.2 实现 `insert`/`search_by_vector`/`search_by_vector_with_tags`/`delete`/`list_by_tags`/`get_all`/`count` 方法
- [x] 2.8 重写 `teamaivectormemory/db/state_repo.py`
  - [x] 2.8.1 适配 PostgreSQL 语法，`session_state` UNIQUE 约束改为 `(project_dir, user_id)`
  - [x] 2.8.2 `session_id` 按 `(project_dir, user_id)` 独立递增
- [x] 2.9 重写 `teamaivectormemory/db/issue_repo.py`
  - [x] 2.9.1 适配 PostgreSQL 语法，所有查询/写入增加 `user_id` 过滤
- [x] 2.10 重写 `teamaivectormemory/db/task_repo.py`
  - [x] 2.10.1 适配 PostgreSQL 语法，所有查询/写入增加 `user_id` 过滤
- [x] 2.11 更新 `teamaivectormemory/db/__init__.py`
  - [x] 2.11.1 新增 `TeamMemoryRepo` 导出
- [x] 2.12 编写 PostgreSQL 建表验证脚本，连接数据库确认表结构和 pgvector 扩展正常

## 第 3 组：F4 团队共享记忆（team scope）+ F3 用户隔离（工具层）

- [x] 3.1 修改 `gatewayaivectormemory/tools/remember.py`
  - [x] 3.1.1 `scope` 枚举新增 `"team"`，写入 `team_memories` 表
  - [x] 3.1.2 接收 `user_id` 参数，project scope 写入时关联 `user_id`，team scope 写入时记录 `created_by`
- [x] 3.2 修改 `gatewayaivectormemory/tools/recall.py`
  - [x] 3.2.1 `scope: "team"` 只搜索 `team_memories`
  - [x] 3.2.2 `scope: "all"` 同时搜索 `memories` + `team_memories` + `user_memories`，各表取 `top_k` 后合并，按相似度统一排序，取最终 `top_k` 条
  - [x] 3.2.3 `scope: "project"` 只搜索 `memories`（按 `user_id` 过滤）
- [x] 3.3 修改 `gatewayaivectormemory/tools/forget.py`
  - [x] 3.3.1 支持删除 `team_memories` 中的记忆
- [x] 3.4 修改 `gatewayaivectormemory/tools/status.py`
  - [x] 3.4.1 接收 `user_id` 参数，按 `(project_dir, user_id)` 读写状态（db 层已实现）
- [x] 3.5 修改 `gatewayaivectormemory/tools/track.py`
  - [x] 3.5.1 接收 `user_id` 参数，所有操作按 `user_id` 隔离（db 层已实现）
- [x] 3.6 修改 `gatewayaivectormemory/tools/task.py`
  - [x] 3.6.1 接收 `user_id` 参数，所有操作按 `user_id` 隔离（db 层已实现）
- [x] 3.7 修改 `gatewayaivectormemory/tools/auto_save.py`
  - [x] 3.7.1 接收 `user_id` 参数，写入 `user_memories` 时关联 `user_id`（db 层已实现）
- [x] 3.8 更新 `gatewayaivectormemory/tools/__init__.py`
  - [x] 3.8.1 `TOOL_DEFINITIONS` 中 `remember` 的 `scope` 枚举新增 `"team"`
  - [x] 3.8.2 `recall` 的 `scope` 枚举新增 `"team"`

## 第 4 组：F2 Memory Proxy HTTP 服务 + F5 配置管理 + F6 Embed Server 复用

- [ ] 4.1 新建 `teamaivectormemory/proxy/__init__.py`
- [ ] 4.2 新建 `teamaivectormemory/proxy/app.py`
  - [ ] 4.2.1 FastAPI 应用：创建 `app` 实例，注册中间件（CORS、请求日志）
  - [ ] 4.2.2 启动时初始化 PostgreSQL 连接池、验证 embed-server 连通性
  - [ ] 4.2.3 `GET /memory/health` 健康检查端点（含 PostgreSQL 连通性 + Embed Server 连通性）
- [ ] 4.3 新建 `teamaivectormemory/proxy/routes.py`
  - [ ] 4.3.1 实现 REST API 端点：`POST /memory/remember`、`POST /memory/recall`、`POST /memory/forget`、`POST /memory/status`、`POST /memory/track`、`POST /memory/task`、`POST /memory/auto_save`
  - [ ] 4.3.2 从 `X-User-Id` Header 提取 `user_id`（必传，缺失返回 400）
  - [ ] 4.3.3 从 `X-Project-Dir` Header 提取 `project_dir`（必传，缺失返回 400）
  - [ ] 4.3.4 请求体与现有工具 `arguments` 一致，调用 `TOOL_HANDLERS` 处理
  - [ ] 4.3.5 统一响应格式：`{"success": true/false, "data": {...}, "error": "..."}`
- [ ] 4.4 新建 `teamaivectormemory/proxy/middleware.py`
  - [ ] 4.4.1 请求日志中间件：记录 `user_id`、`project_dir`、`tool`、`latency`
- [ ] 4.5 修改 `teamaivectormemory/__main__.py`
  - [ ] 4.5.1 新增 `memory-proxy` 子命令，参数：`--port`（默认 8080）、`--bind`（默认 0.0.0.0）、`--pg-url`（必传）、`--embed-url`（必传）、`--token`、`--jwt-secret`、`--user-tokens`、`--workers`（默认 4）
  - [ ] 4.5.2 `memory-proxy` 子命令启动 uvicorn + 多 worker
  - [ ] 4.5.3 支持环境变量 `TEAMAIVECTORMEMORY_PG_URL`、`TEAMAIVECTORMEMORY_EMBED_URL`
- [ ] 4.6 修改 `teamaivectormemory/embedding/engine.py`
  - [ ] 4.6.1 确认 `--embed-url` 远程模式正常工作（已有实现，验证即可）
- [ ] 4.7 编写 Memory Proxy 启动验证脚本：启动服务 → 调用 `/memory/health` → 验证响应

## 第 5 组：F7 认证与鉴权

- [ ] 5.1 新建 `teamaivectormemory/proxy/auth.py`
  - [ ] 5.1.1 实现静态 token 认证：从 `Authorization: Bearer <token>` Header 提取 token，与 `--token` 比对
  - [ ] 5.1.2 实现 `--user-tokens` JSON 文件加载：token → user_id 映射，匹配时覆盖 `X-User-Id`，角色为 `user`
  - [ ] 5.1.3 `--token` 匹配时角色为 `admin`
  - [ ] 5.1.4 实现 JWT 认证：`--jwt-secret` 验签，从 payload 提取 `user_id` 和 `role`，`user_id` 优先于 `X-User-Id` Header
  - [ ] 5.1.5 `--token` 与 `--jwt-secret` 互斥校验（启动时报错）
- [x] 5.2 实现角色权限控制
  - [ ] 5.2.1 `admin` 角色：可查看所有用户数据、所有项目数据
  - [ ] 5.2.2 `user` 角色：只能查看自己的数据 + 所属项目的 team 记忆
  - [ ] 5.2.3 在路由层根据角色过滤数据访问
- [x] 5.3 安全默认值
  - [ ] 5.3.1 不启用认证时：仅允许 `127.0.0.1` 访问（中间件检查 `request.client.host`）
  - [ ] 5.3.2 `--bind 0.0.0.0` 且未设认证时启动警告提示
- [x] 5.4 认证未通过时返回 401 Unauthorized

## 第 6 组：Web 看板适配

- [ ] 6.1 修改 `teamaivectormemory/web/app.py`
  - [ ] 6.1.1 改为连接 PostgreSQL（接收 `--pg-url` 参数）
  - [ ] 6.1.2 支持 `--user-id` 参数过滤（不传时展示全部 = 管理员模式）
  - [ ] 6.1.3 支持 `--embed-url` 参数（语义搜索通过远程 embed-server）
- [ ] 6.2 修改 `teamaivectormemory/web/api.py`
  - [ ] 6.2.1 所有 API 增加 `user_id` 过滤逻辑
  - [ ] 6.2.2 记忆列表增加 `scope` 筛选（project / team / user）
  - [ ] 6.2.3 team 记忆显示 `created_by` 标记
- [ ] 6.3 修改 `teamaivectormemory/web/static/app.js`
  - [ ] 6.3.1 记忆列表增加 scope 筛选 UI（project / team / user）
  - [ ] 6.3.2 team 记忆显示 created_by 标记
- [x] 6.4 Web 看板认证
  - [ ] 6.4.1 启用 token 时展示登录页，输入 token 后存 localStorage
  - [ ] 6.4.2 后续请求自动带 `Authorization: Bearer <token>` Header
  - [ ] 6.4.3 登出清除 localStorage
- [ ] 6.5 修改 `teamaivectormemory/__main__.py` 中 `web` 子命令
  - [ ] 6.5.1 新增 `--pg-url`、`--embed-url`、`--user-id` 参数
- [x] 6.6 验证看板启动和基本功能

## 第 7 组：文档更新 + readme 工具更新

- [ ] 7.1 修改 `teamaivectormemory/tools/readme.py`
  - [ ] 7.1.1 移除 SQLite 相关描述（`_generate_deps_section` 中 "Vector DB | SQLite + sqlite-vec"）
  - [ ] 7.1.2 移除 "Protocol | Model Context Protocol (MCP)" 描述
  - [ ] 7.1.3 更新为 PostgreSQL + pgvector + HTTP 技术栈描述
- [ ] 7.2 重写 `README.md`：PostgreSQL + HTTP Memory Proxy 用法
- [ ] 7.3 重写 `docs/` 下 6 个多语言 README
  - [ ] 7.3.1 `docs/README.en.md`
  - [ ] 7.3.2 `docs/README.zh-TW.md`
  - [ ] 7.3.3 `docs/README.ja.md`
  - [ ] 7.3.4 `docs/README.de.md`
  - [ ] 7.3.5 `docs/README.fr.md`
  - [ ] 7.3.6 `docs/README.es.md`

## 第 8 组：集成测试 + 最终验证

- [ ] 8.1 端到端测试：`team-run memory-proxy --pg-url ... --embed-url ...` 启动 → 调用全部 REST API → 验证响应
- [ ] 8.2 用户隔离测试：不同 `X-User-Id` 的数据互不可见
- [ ] 8.3 team scope 测试：同 `project_dir` 不同 `user_id` 可共享 team 记忆
- [ ] 8.4 认证测试：启用 token 后无 token 请求返回 401
- [ ] 8.5 Web 看板测试：启动看板 → 验证 scope 筛选 + user_id 过滤
- [ ] 8.6 确认旧代码已完全清除：`grep -r "sqlite" teamaivectormemory/` 无匹配、`server.py`/`protocol.py`/`install.py` 不存在
- [ ] 8.7 确认项目只能通过 `team-run memory-proxy` / `team-run web` / `team-run embed-server` 启动
