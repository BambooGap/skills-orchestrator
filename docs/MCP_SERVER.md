# MCP Server

Skills Orchestrator exposes a stdio MCP server for runtime skill routing.

## Install MCP Runtime

The default PyPI package is a lightweight CI governance CLI. Install the optional MCP runtime extra
before using `serve` or `mcp-test`:

```bash
python3.12 -m pip install "skills-orchestrator[mcp]"
```

Use `pipx`, `uv tool`, a dedicated virtual environment, or the repository Dockerfile. Do not install
the MCP extra into an existing business FastAPI environment. In particular, FastAPI `0.116.1` and
the current MCP transport dependencies have incompatible Starlette requirements. The release-tested,
version-constrained deployment set is published as `constraints-mcp.txt`; it does not contain
artifact hashes and is not a hash lock. Use it only in an isolated MCP environment, then require
both `python -m pip check` and a real protocol smoke:

```bash
python3.12 -m venv .venv-skillops-mcp
. .venv-skillops-mcp/bin/activate
python -m pip install \
  --constraint constraints-mcp.txt \
  "skills-orchestrator[mcp]==<matching-version>"
python -m pip check
skills-orchestrator mcp-test list_skills '{}' --config /absolute/path/to/config/skills.yaml
```

The project tests Python 3.12 and 3.13, the minimum supported MCP `1.0.0`, the latest compatible
MCP 1.x, FastAPI `0.140.0` with an HTTP 200 smoke, and the known-unsupported FastAPI `0.116.1`
shared-environment case. It deliberately does not force a lower Starlette ceiling.

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
hashes, active skill IDs, zone, and registry generation. Events carry a sequence number, previous
event hash, and event hash. Production Pipeline events additionally record non-sensitive pipeline,
run, step, execution, evidence-digest, and verifier identifiers. It does not store raw task text or
skill content.

Audit remains best-effort for ordinary MCP routing and `coordination` Pipelines. A `production`
Pipeline requires `--audit-dir`; a missing sink or write failure stops the production state
transition. Every strict production append validates the complete chain rather than only the tail.
Production step results are durably recorded in an approval outbox before a passing event is
written. The outbox is bound to the canonical audit directory and stable event payload; recovery
refuses a changed sink or conflicting event ID. Successful writes clear the outbox immediately.
An interrupted audit remains `pending_audit` and is idempotently recovered on retry.

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

Reports verify the complete hash chain by default and fail closed on damaged data. For incident
inspection only, `--best-effort` skips chain verification and marks the output
`unverified_best_effort`; do not use that mode for production decisions.

`audit_integrity` distinguishes `disabled`, `missing`, `empty`, `verified`, and
`unverified_best_effort`. Only `verified` means that a non-empty audit chain exists and passed
validation. A configured audit directory without `events.jsonl` returns `missing` and a non-zero
CLI exit code.

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
