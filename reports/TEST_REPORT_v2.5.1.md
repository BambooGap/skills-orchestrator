# Test Report v2.5.1

Date: 2026-06-21

## Scope

v2.5.1 is a project-page and package-metadata refresh:

- Updated GitHub/PyPI/Action positioning around SkillOps and instruction supply chain.
- Refreshed README first-viewport copy and CI examples.
- Preserved the v2.5.0 Registry & Evidence behavior without core logic changes.

## Local Verification

```bash
PATH="$PWD/.venv312-test/bin:$PATH" .venv312-test/bin/python -m pytest -q
```

Result: 361 passed.

```bash
PATH="$PWD/.venv312-test/bin:$PATH" .venv312-test/bin/ruff check skills_orchestrator/ tests/ scripts/check_action_pins.py
PATH="$PWD/.venv312-test/bin:$PATH" .venv312-test/bin/ruff format --check skills_orchestrator/ tests/ scripts/check_action_pins.py
```

Result: ruff check passed; 76 files already formatted.

```bash
python3 scripts/check_action_pins.py
```

Result: all third-party GitHub Actions are pinned to full commit SHAs.

```bash
PATH="$PWD/.venv312-test/bin:$PATH" .venv312-test/bin/skills-orchestrator doctor \
  --config config/skills.yaml \
  --check-lock skills.lock.json \
  --fail-under 100
```

Result: commercial readiness 100/100.

```bash
rm -rf dist build skills_orchestrator.egg-info
PATH="$PWD/.venv312-test/bin:$PATH" .venv312-test/bin/python -m build
PATH="$PWD/.venv312-test/bin:$PATH" .venv312-test/bin/python -m twine check dist/*
```

Result: wheel and sdist built as `2.5.1`; twine metadata check passed.

## Release Verification

```bash
skills-orchestrator --version
```

Expected: `skills-orchestrator, version 2.5.1`.
