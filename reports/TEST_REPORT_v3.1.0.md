# skills-orchestrator v3.1.0 Test Report

Date: 2026-06-21

## Scope

This report covers the v3.1.0 Engineering-Grade Pack:

- `conformance run`
- `builtin/engineering-grade`
- local declarative policy packs
- `doctor --profile enterprise`
- `conformance` and `policy-pack` schema contracts
- registry diff review-window field rendering

## Verification

| Check | Result |
| --- | --- |
| `PATH="$PWD/.venv/bin:$PATH" .venv/bin/python -m pytest -q` | PASS, 431 passed |
| `.venv/bin/python -m ruff check .` | PASS |
| `git diff --check` | PASS |
| `.venv/bin/python -m build` | PASS, built `skills_orchestrator-3.1.0.tar.gz` and wheel |
| `.venv/bin/python -m twine check dist/skills_orchestrator-3.1.0*` | PASS |
| `.venv/bin/python scripts/check_action_pins.py` | PASS |
| `skills-orchestrator conformance run --config config/skills.yaml --policy-pack builtin/team-standard --format json` | PASS, 9/9 steps |
| `skills-orchestrator schema validate --kind policy-pack --input examples/policy/engineering-grade-pack.yaml` | PASS |
| `skills-orchestrator check --config config/skills.yaml --policy-pack builtin/engineering-grade --format json` | PASS, 0 errors, 21 review-window warnings |

## Review Fixes

The code-review pass found three non-blocking issues, all fixed before this report:

- `SO015` now strictly requires `YYYY-MM-DD`, not compact ISO dates.
- `doctor --profile enterprise` now resolves relative evidence artifact paths across common export
  invocation directories.
- `conformance run --fail-on warning` no longer treats info-only diagnostics as warning failures.

## Skipped

| Check | Reason |
| --- | --- |
| `pip-audit` | Not installed in the current local environment. |
| `pip check` | The current `.venv` does not include the `pip` module. |

## Notes

`builtin/engineering-grade` is intentionally stricter than the default `builtin/team-standard`.
The repository's current skills pass without errors but emit review-window warnings until
`reviewed_at` and `expires_at` are added to each skill.
