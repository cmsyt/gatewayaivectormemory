#!/usr/bin/env bash
# AIVectorMemory PreToolUse Hook - 检查当前项目是否有活跃的 track issue
# 用于 Claude Code / Kiro 的 PreToolUse hook
# 如果没有活跃 issue，exit 2 拒绝工具执行

DB_PATH="$HOME/.aivectormemory/memory.db"

# 数据库不存在则放行（首次使用）
if [ ! -f "$DB_PATH" ]; then
  exit 0
fi

# 从环境变量获取项目目录（Claude Code / Kiro 会设置 PWD）
PROJECT_DIR="${PROJECT_DIR:-$(pwd)}"

# 查询当前项目是否有活跃 issue（status = pending 或 in_progress）
COUNT=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM issues WHERE project_dir='$PROJECT_DIR' AND status IN ('pending','in_progress');" 2>/dev/null)

# 查询失败（表不存在等）则放行
if [ $? -ne 0 ] || [ -z "$COUNT" ]; then
  exit 0
fi

# 有活跃 issue 则放行
if [ "$COUNT" -gt 0 ]; then
  exit 0
fi

# 没有活跃 issue，拒绝执行并提示
echo "⚠️ 当前项目没有活跃的 track issue。请先调用 track(action: create) 记录问题后再修改代码。" >&2
exit 2
