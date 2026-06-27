# MCP Server

Skills Orchestrator exposes a stdio MCP server for runtime skill routing.

## Install MCP Runtime

The default PyPI package is a lightweight CI governance CLI. Install the optional MCP runtime extra
before using `serve` or `mcp-test`:

```bash
python3.12 -m pip install "skills-orchestrator[mcp]"
```

## Start The Server

```bash
skills-orchestrator serve --config /absolute/path/to/config/skills.yaml
```

For a fixed zone:

```bash
skills-orchestrator serve \
  --config /absolute/path/to/config/skills.yaml \
  --zone enterprise \
  --max-content-bytes 40000
```

## Client Configuration

Example client configuration:

```json
{
  "mcpServers": {
    "skills-orchestrator": {
      "command": "skills-orchestrator",
      "args": [
        "serve",
        "--config",
        "/absolute/path/to/config/skills.yaml"
      ]
    }
  }
}
```

Use absolute paths in MCP client configuration so the server can start from any working directory.

## Runtime Contract

Use `prepare_context` at each task boundary:

```json
{
  "task": "review this pull request for security issues",
  "max_skills": 3,
  "include_content": true
}
```

The response contains:

- `active_skills`: skills that apply to the current task,
- `inactive_skills`: registry skills not selected for this task,
- `Decision Record (JSON)`: structured routing evidence with `routing_id`, `task_hash`,
  `task_hash_alg`, registry generation, active/inactive skills, content hashes, and truncation
  metadata,
- an execution rule that says old skills from prior tasks should not control the current task,
- optional full skill content when `include_content` is true.

This is the main defense against stale instructions leaking across unrelated work.

## Audit Events

Runtime audit is opt-in:

```bash
skills-orchestrator serve \
  --config /absolute/path/to/config/skills.yaml \
  --audit-dir /absolute/path/to/.skills-audit
```

The audit log is JSONL at `events.jsonl`. It records tool names, argument keys, outcomes, routing
hashes, active skill IDs, zone, and registry generation. It does not store raw task text or skill
content.

By default `task_hash` is deterministic SHA-256 for local correlation. For commercial or multi-tenant
audit logs, set a private salt so hashes use HMAC-SHA256:

```bash
export SKILLS_ORCHESTRATOR_AUDIT_SALT="$(openssl rand -hex 32)"
```

Audit directories and files are written with private permissions where the OS supports chmod.

Generate a compact report:

```bash
skills-orchestrator usage report --audit-dir /absolute/path/to/.skills-audit
skills-orchestrator usage report --audit-dir /absolute/path/to/.skills-audit --json
```

## Runtime Content Limits

`get_skill`, `prepare_context`, and Pipeline step injection enforce a per-skill content byte limit.
The default is `40000` bytes. Configure it with either CLI or environment:

```bash
skills-orchestrator serve \
  --config /absolute/path/to/config/skills.yaml \
  --max-content-bytes 30000

export SKILLS_ORCHESTRATOR_MAX_CONTENT_BYTES=30000
```

Set `--max-content-bytes 0` only for trusted local debugging. Truncated responses include a visible
notice and the decision record lists `content_limits.truncated_skill_ids`.

## Local Tool Testing

You can test MCP tools without starting a long-running server:

```bash
skills-orchestrator mcp-test list_skills '{}' --config config/skills.yaml

skills-orchestrator mcp-test prepare_context \
  '{"task": "write release notes", "max_skills": 3, "include_content": false}' \
  --config config/skills.yaml
```

## Available Tools

- `list_skills`
- `search_skills`
- `get_skill`
- `suggest_combo`
- `prepare_context`
- `pipeline_start`
- `pipeline_status`
- `pipeline_advance`
- `pipeline_resume`
- `pipeline_list_runs`

## Operational Notes

- Restart the MCP server after changing skills or `config/skills.yaml`.
- Keep the server read-only from the model's perspective; tools return instruction content and
  workflow state but do not mutate source-controlled skills.
- Avoid logging tool argument values. The server logs only argument keys for debug visibility.
