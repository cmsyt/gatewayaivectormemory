# 需求文档：用户级数据隔离 + 团队共享记忆

> 前置依赖：`.kiro/specs/shared-embedding-and-user-isolation/`（Embedding 共享服务）需先完成

## 背景

teamaivectormemory 集成到 API Gateway 后，团队成员通过本地 IDE 经网关连接服务器上的 MCP worker。当前所有数据按 project_dir 隔离，缺少用户维度，导致：
1. 多用户共享同一 project_dir 时，个人记忆、issues、tasks、session_state 互相可见
2. 团队踩坑经验无法共享，每个人独立踩同样的坑

## 应用场景

### 场景 1：团队共享开发服务器

```
服务器
├── Embed Server（单进程，200MB）
├── Worker-A1  --user-id a1  --project-dir /srv/project-x
├── Worker-A2  --user-id a2  --project-dir /srv/project-x
├── Worker-A3  --user-id a3  --project-dir /srv/project-x
└── ~/.teamaivectormemory/memory.db（共享）
```

记忆隔离：
- A1 用 `remember(scope="project")` → 只有 A1 能看到（project_dir + user_id）
- A1 用 `remember(scope="team")` → A1/A2/A3 都能看到（project_dir，无 user_id 过滤）
- A1 用 `auto_save` 存偏好 → 只有 A1 能看到（user_memories，user_id 隔离）
- A1 的 issues/tasks/session_state → 只有 A1 能看到（user_id 隔离）

### 场景 2：多团队多项目服务器

```
服务器
├── Embed Server
├── 团队 A（project-x）
│   ├── Worker --user-id a1 --project-dir /srv/project-x
│   ├── Worker --user-id a2 --project-dir /srv/project-x
│   └── Worker --user-id a3 --project-dir /srv/project-x
├── 团队 B（project-y）
│   ├── Worker --user-id b1 --project-dir /srv/project-y
│   └── Worker --user-id b2 --project-dir /srv/project-y
└── ~/.teamaivectormemory/memory.db（共享）
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

## 功能一：用户级数据隔离

### 需求描述

增加 `user_id` 维度，确保多用户共享服务器时个人数据互不可见。

### 功能范围

1. user_id 传入方式（优先级从高到低）
   - `--user-id` 命令行参数
   - `TEAMAIVECTORMEMORY_USER_ID` 环境变量
   - 默认空字符串（向后兼容）
2. 数据库 schema 变更（v10 迁移）
   - memories 表加 `user_id TEXT NOT NULL DEFAULT ''`
   - issues / issues_archive 加 `user_id`
   - tasks / tasks_archive 加 `user_id`
   - session_state 加 `user_id`，UNIQUE 改为 `(project_dir, user_id)`
   - user_memories 加 `user_id`
   - 现有数据 user_id 默认空字符串，无损迁移
3. 数据访问层改造
   - ConnectionManager 增加 `user_id` 属性
   - 所有 Repo 类查询/写入增加 user_id 过滤
4. MCP Server 改造
   - MCPServer.__init__ 接收 user_id
   - session_id 按 (project_dir, user_id) 递增
5. Web 看板改造
   - 支持 `--user-id` 参数过滤
   - 不传时展示全部（管理员模式）
6. install 命令
   - MCP 配置增加 `TEAMAIVECTORMEMORY_USER_ID` 环境变量占位说明

### 验收标准

- [ ] `--user-id a1` 只能看到 a1 的数据
- [ ] 环境变量方式等效
- [ ] 不传时行为不变
- [ ] schema 迁移平滑
- [ ] 同 project_dir 不同 user_id 的数据互不可见
- [ ] 不同 user_id 的 user_memories 互不可见
- [ ] 看板按 user_id 过滤
- [ ] session_id 按 (project_dir, user_id) 独立递增

---

## 功能二：团队共享记忆（team scope）

### 需求描述

新增 `scope: "team"` 记忆层，存储在独立表中，同一 project_dir 下所有用户可见，用于共享踩坑经验、架构知识等团队级信息。

### 三层记忆体系

| scope | 存储表 | 向量表 | 隔离维度 | 用途 |
|-------|--------|--------|----------|------|
| user | user_memories | vec_user_memories | user_id | 个人偏好，跨项目 |
| project | memories | vec_memories | project_dir + user_id | 个人项目记忆 |
| team | team_memories（新） | vec_team_memories（新） | project_dir | 团队共享记忆 |

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
- `auto_save` 始终写入 `user` scope（行为不变）

### 功能范围

1. 新增数据库表
   - `team_memories`：结构同 memories，按 project_dir 隔离，不含 user_id 过滤
   - `vec_team_memories`：对应向量表
2. remember 工具扩展
   - `scope: "team"` 写入 team_memories 表
   - 写入时记录 `created_by`（user_id），标记谁创建的，但不影响可见性
3. recall 工具扩展
   - `scope: "team"` 只搜索 team_memories
   - `scope: "all"` 同时搜索 memories + team_memories + user_memories，合并结果
   - `scope: "project"` 只搜索 memories（个人项目记忆，行为不变）
4. forget 工具扩展
   - 支持删除 team_memories 中的记忆
5. Web 看板
   - 记忆列表增加 scope 筛选（project / team / user）
   - team 记忆显示 created_by 标记

### 验收标准

- [ ] `remember(scope="team")` 写入 team_memories 表
- [ ] 同 project_dir 的所有 user_id 都能 recall 到 team 记忆
- [ ] 不同 project_dir 的 team 记忆互不可见
- [ ] `recall(scope="all")` 合并三张表的搜索结果
- [ ] `recall(scope="project")` 行为不变
- [ ] team 记忆记录 created_by 字段
- [ ] 看板支持 scope 筛选
- [ ] 去重逻辑在 team_memories 表内独立运行

---

## 不在范围内

- 用户认证/鉴权（由网关层负责）
- 多数据库实例（继续单 SQLite 文件）
- embedding 模型切换/自定义模型
- 用户管理界面（user_id 由外部传入）
- 数据加密（文件权限保障）
- team 记忆的权限控制（如只读/读写）
