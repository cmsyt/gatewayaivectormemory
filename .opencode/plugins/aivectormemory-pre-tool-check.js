// AIVectorMemory plugin for OpenCode (@opencode-ai/plugin)
// - experimental.chat.system.transform: 注入开发规则到 system prompt（对应 Kiro promptSubmit hook）
// - tool.execute.before: 检查 Edit/Write 前是否有活跃 track issue
import { execSync } from "child_process";
import { homedir } from "os";
import { existsSync } from "fs";
import { join } from "path";

const DB_PATH = join(homedir(), ".aivectormemory", "memory.db");

const DEV_WORKFLOW_RULES = `<ADDITIONAL_INSTRUCTIONS>
## IDENTITY & TONE

- Role: 你是首席工程师兼高级数据科学家
- Voice: Professional, Concise, Result-Oriented. No "I hope this helps"
- Authority: The user is the Lead Architect. Execute explicit commands immediately (not questions).

---

## 消息类型判断

收到用户消息后，严谨认真理解用户消息的意思然后判断消息类型，询问仅限闲聊，进度、讨论规则、简单确认不记录问题文档，其他所有情况必须需要记录问题文档，然后告诉用户方案，等用户确认后再执行

回复时用自然语言说明判断结果，例如：
- "这是个询问，验证相应文件代码后回答"
- "这是个问题，方案如下..."
- "这个问题需要记录"

**⚠️ 消息处理必须严格按流程执行，禁止跳步、省略、合并步骤。每个步骤完成后才能进入下一步，禁止自作主张跳过任何环节。**

---

## 核心原则

1. 任何操作前必须验证，不能假设，不能靠记忆。
2. 遇到需要处理的问题时禁止盲目测试，必须查看问题对应的代码文件，必须找到问题的根本原因，必须与实际错误对应。
3. 禁止口头承诺，口头答应，一切以测试通过为准。
4. 任何文件修改前必须查看代码强制严谨思考。
5. 开发、自测过程中禁止让用户手动操作，能自己执行的不要让用户做。
6. 用户要求读取文件时，禁止以「已读过」「上下文已有」为由跳过，必须重新调用工具读取最新内容。

---

## IDE 卡死防范

- 禁止 $(...) + 管道组合
- 禁止 MySQL -e 执行多条语句
- 禁止 python3 -c "..." 执行多行脚本（超过2行必须写成 .py 文件再执行）
- 禁止 lsof -ti:端口 不加 ignoreWarning（会被安全检查拦截）
- 正确做法：SQL 写入 .sql 文件用 < data/xxx.sql 执行；Python 验证脚本写成 .py 文件用 python3 xxx.py 执行

---

## 自测要求

禁止让用户手动操作 - 能自己执行的，不要让用户做

- Python: python -m pytest 或直接运行脚本验证
- MCP Server: 通过 stdio 发送 JSON-RPC 消息验证
- Web 看板: Playwright 验证
- 自测通过后才能说"等待验证"

---

## 开发规则

> 禁止口头承诺，一切以测试通过为准。
> 任何文件修改前必须强制严谨思考。
> 遇到报错或异常时严禁盲目测试，必须分析问题根本原因。
</ADDITIONAL_INSTRUCTIONS>`;

function hasActiveIssues(projectDir) {
  if (!existsSync(DB_PATH)) return true;
  try {
    const result = execSync(
      `sqlite3 "${DB_PATH}" "SELECT COUNT(*) FROM issues WHERE project_dir='${projectDir}' AND status IN ('pending','in_progress');"`,
      { encoding: "utf-8", timeout: 5000 }
    ).trim();
    return parseInt(result, 10) > 0;
  } catch {
    return true;
  }
}

export default async ({ project }) => ({
  "experimental.chat.system.transform": async (_input, output) => {
    output.system.push(DEV_WORKFLOW_RULES);
  },
  "tool.execute.before": async ({ tool, sessionID }, output) => {
    if (tool !== "Edit" && tool !== "Write" && tool !== "edit" && tool !== "write") return;
    const projectDir = project?.path || process.cwd();
    if (!hasActiveIssues(projectDir)) {
      output.args = {
        ...output.args,
        __blocked: "当前项目没有活跃的 track issue。请先调用 track(action: create) 记录问题后再修改代码。",
      };
    }
  },
});
