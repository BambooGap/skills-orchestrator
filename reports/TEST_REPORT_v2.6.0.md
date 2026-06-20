# Test Report v2.6.0

Date: 2026-06-21

## Scope

v2.6.0 adds three P0 commercial surfaces:

- `schema validate` for native config and JSON artifact contracts.
- `init --template team-standard` for portable team bootstrap.
- `registry diff --format markdown` for PR/release review.

## Automated Verification

```bash
uv run --extra dev pytest -q
```

Result: `383 passed in 2.04s`

```bash
uv run --extra dev ruff check skills_orchestrator tests
```

Result: `All checks passed!`

```bash
uv run --extra dev ruff format --check skills_orchestrator tests
```

Result: `78 files already formatted`

## Focused Verification

```bash
uv run --extra dev pytest -q tests/test_schema_cmd.py tests/test_init_cmd.py tests/test_commercial_surfaces.py
```

Result: `36 passed in 0.35s`

## Manual Smoke

```bash
skills-orchestrator init --template team-standard
skills-orchestrator check --config config/skills.yaml --policy-pack builtin/team-standard --fail-on warning
skills-orchestrator schema validate --kind config --input config/skills.yaml
skills-orchestrator build --config config/skills.yaml --lock
```

Result:

- generated `config/skills.yaml`, three starter skills, review pipeline, GitHub Actions workflow,
  and `evidence/.gitkeep`;
- check passed with `0 errors, 0 warnings, 0 infos`;
- schema validation passed;
- build generated `AGENTS.md` and `skills.lock.json`.

```bash
skills-orchestrator registry diff before.json after.json --format markdown --output diff.md
skills-orchestrator schema validate --kind registry-diff --input registry-diff.json
```

Result:

- Markdown diff rendered summary and changed-skill sections;
- registry diff schema validation passed.

## Package Verification

```bash
rm -rf dist build *.egg-info
uv run --extra dev python -m build
uv run --extra dev python -m twine check dist/*
/opt/homebrew/opt/python@3.12/bin/python3.12 -m venv /tmp/skills-orchestrator-wheel-smoke
uv pip install --python /tmp/skills-orchestrator-wheel-smoke/bin/python dist/*.whl
/tmp/skills-orchestrator-wheel-smoke/bin/skills-orchestrator schema list --format json
/tmp/skills-orchestrator-wheel-smoke/bin/skills-orchestrator schema validate --kind config --input config/skills.yaml
```

Result:

- built `skills_orchestrator-2.6.0.tar.gz`;
- built `skills_orchestrator-2.6.0-py3-none-any.whl`;
- `twine check` passed for both distributions;
- wheel includes `skills_orchestrator/schemas/*.schema.json`;
- installed wheel in a Python 3.12 virtual environment and validated packaged schema resources.

## Supply Chain Checks

```bash
uv run --extra dev python scripts/check_action_pins.py
```

Result: `All third-party GitHub Actions are pinned to full commit SHAs.`
