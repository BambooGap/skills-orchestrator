# Test Report v3.0.6

Date: 2026-06-21

## Scope

Validated the v3.0.6 credibility patch:

- upgraded CodeQL Action references from pinned v3 SHA to pinned v4 SHA;
- removed PATH dependence from subprocess-based CLI tests;
- documented and smoke-tested the demo repository's local changed registry diff flow;
- aligned current docs and package metadata with release version `3.0.6`.

## Commands

```bash
env PATH=/usr/bin:/bin .venv/bin/python -m pytest \
  tests/test_sync.py::TestSyncCLI \
  tests/test_e2e.py::TestE2ECLIIntegration -q

uv run --extra dev pytest -q
uv run --extra dev ruff check .
uv run --extra dev ruff format --check .
python3.12 scripts/check_action_pins.py
uv run --with pip-audit==2.10.1 pip-audit --strict --requirement constraints.txt
rm -rf dist && uv run --extra dev python -m build && uv run --extra dev twine check dist/*
```

## Results

- PATH-hermetic subprocess CLI tests: `6 passed`
- Full test suite: `417 passed`
- Ruff check: passed
- Ruff format check: passed
- GitHub Action pinning check: passed
- pip-audit: no known vulnerabilities found
- Package build: produced `skills_orchestrator-3.0.6.tar.gz` and `skills_orchestrator-3.0.6-py3-none-any.whl`
- Twine package validation: passed for both artifacts

## Demo Diff Smoke

Copied `examples/demo-repo` to a temporary directory and ran the documented changed-diff flow:

- built `evidence/registry-before.json`;
- changed `skills/release-checklist.md` from `version: 1.0.0` to `version: 1.0.1`;
- built `evidence/registry-after.json`;
- generated Markdown diff and PR comment body;
- validated the JSON registry diff against `registry-diff` schema.

Observed output included:

- `Changed | 1`;
- owner `release-team`;
- path `skills/release-checklist.md`;
- registry key `config/skills.yaml::skills/release-checklist.md::release-checklist`;
- governance detail `version 1.0.0 -> 1.0.1`.

## Wheel Smoke

Installed the locally built wheel into a clean Python 3.12 virtual environment and verified:

- `skills-orchestrator --version` reports `3.0.6`;
- `pipeline list` loads packaged pipeline resources outside the source tree.

