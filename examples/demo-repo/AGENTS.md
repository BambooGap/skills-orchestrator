# Demo Agent Instructions

Use Skills Orchestrator as the source of truth for task-scoped skills in this repository.

At a task boundary, call the MCP `prepare_context` tool with a short task description. Follow only
the returned active skills for the current task.
