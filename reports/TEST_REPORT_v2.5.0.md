# Test Report v2.5.0

Date: 2026-06-21

## Release Scope

v2.5.0 is the Registry & Evidence commercial-readiness slice:

- built-in `builtin/team-standard` policy pack,
- governance metadata in parser, manifest, CycloneDX, and OPA exports,
- `doctor` commercial-readiness report,
- `registry build` and `registry diff`,
- `evidence export` bundle,
- `integrations list` ecosystem catalog,
- MCP content byte limits and optional HMAC task hashing,
- private audit/pipeline file permissions,
- pipeline context redaction before persistence.

## Local Verification

```bash
PATH="$PWD/.venv312-test/bin:$PATH" .venv312-test/bin/python -m pytest -q
```

Result: 361 passed.

```bash
.venv312-test/bin/ruff format --check skills_orchestrator/ tests/ scripts/check_action_pins.py
.venv312-test/bin/ruff check skills_orchestrator/ tests/ scripts/check_action_pins.py
python3 scripts/check_action_pins.py
```

Result: formatting passed, lint passed, and all third-party GitHub Actions are pinned to full
commit SHAs.

```bash
PATH="$PWD/.venv312-test/bin:$PATH" .venv312-test/bin/python -m build
PATH="$PWD/.venv312-test/bin:$PATH" .venv312-test/bin/python -m twine check dist/*
```

Result: wheel and sdist built as `2.5.0`; twine metadata check passed.

## Commercial Smoke Checks

```bash
PATH="$PWD/.venv312-test/bin:$PATH" \
  .venv312-test/bin/skills-orchestrator check \
  --config config/skills.yaml \
  --policy-pack builtin/team-standard \
  --fail-on warning \
  --check-lock skills.lock.json
```

Result: 21 skills, 0 errors, 0 warnings, 0 infos.

```bash
PATH="$PWD/.venv312-test/bin:$PATH" \
  .venv312-test/bin/skills-orchestrator doctor \
  --config config/skills.yaml \
  --check-lock skills.lock.json \
  --fail-under 100
```

Result: commercial readiness 100/100, status `strong`.

Additional smoke checks validated:

- `skills-orchestrator integrations list --format json`,
- `skills-orchestrator registry build --config-glob config/skills.yaml`,
- `skills-orchestrator evidence export --config config/skills.yaml --out .tmp-evidence`,
- `skills-orchestrator --version` reports `2.5.0`.

## Skipped

Docker daemon was not running locally, so local Docker build was not rerun in this verification
pass. The GitHub Actions Docker job remains the release gate for container build smoke.
