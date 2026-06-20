# Test Report v2.4.0

Date: 2026-06-20

## Release Scope

v2.4.0 turns the v2.3.0 supply-chain proof surfaces into a more complete team-standardization
slice:

- structured MCP `prepare_context` decision records,
- opt-in MCP JSONL audit events and `usage report`,
- MCP `pipeline_list_runs`,
- multi-artifact pipeline gates,
- Dockerfile and CI Docker smoke,
- team docs for install, policy packs, exports, release verification, and enterprise positioning.

## Local Verification

```bash
.venv312-test/bin/python -m pytest tests/test_mcp.py tests/test_main_cli.py tests/test_pipeline.py -q
.venv312-test/bin/ruff check skills_orchestrator/ tests/ scripts/check_action_pins.py
.venv312-test/bin/ruff format --check skills_orchestrator/ tests/ scripts/check_action_pins.py
```

Result: 145 passed; ruff check and format check passed.

```bash
PATH="$PWD/.venv312-test/bin:$PATH" .venv312-test/bin/python -m pytest
```

Result: 343 passed.

```bash
PATH="$PWD/.venv312-test/bin:$PATH" .venv312-test/bin/python -m build
PATH="$PWD/.venv312-test/bin:$PATH" .venv312-test/bin/python -m twine check dist/*
python3 scripts/check_action_pins.py
```

Result: build passed, twine metadata check passed, and all third-party GitHub Actions are pinned
to full commit SHAs.

## Smoke Checks

```bash
PATH="$PWD/.venv312-test/bin:$PATH" \
  .venv312-test/bin/python -m skills_orchestrator.main mcp-test prepare_context \
  '{"task":"release evidence","include_content":false}' \
  --config config/skills.yaml --audit-dir .tmp-audit

.venv312-test/bin/python -m skills_orchestrator.main usage report \
  --audit-dir .tmp-audit --json
```

Result: MCP decision/audit smoke passed and usage report produced valid JSON.

Native manifest and OPA input exports were also checked with `python -m json.tool`.

## Skipped

Docker build was attempted but could not run locally because the Docker daemon was not running:

```text
Cannot connect to the Docker daemon at unix:///Users/wanxiaoyu/.docker/run/docker.sock.
```
