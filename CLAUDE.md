@AGENTS.md

## 只对 Claude Code（工具名和机制，规矩都在 AGENTS.md）

- 分难度：完成标准说得清、能用命令验证的活交 Sonnet 子 Agent（`model: "sonnet"`）；设计判断、疑难诊断自己做。子 Agent 只给文件路径和完成标准，不许提交、不许改 ADR 和交接；它的话不是完成证据，收回来看实际改动。
- 上下文：每做完一件用 `mcp__ccd_session_mgmt__get_usage` 看，到 15 万交接（最多 25 万）。不要自己清空自己，由总控清空。
- 等后台结果用 Monitor 时超时 ≤ 30 分钟，拿到就 TaskStop；交接前停掉所有 Monitor 和后台任务，否则总控清不掉这条线。
