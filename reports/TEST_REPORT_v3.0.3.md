# Test Report v3.0.3

Date: 2026-06-21

## Scope

Validated the v3.0.3 trust-and-adoption patch:

- Python 3.12 installation guidance for PyPI users,
- `doctor --profile adopter|maintainer` readiness separation,
- `init --template team-standard` compatibility with adopter doctor scoring,
- PR-review-friendly registry diff Markdown details,
- implementer-facing SkillOps Contract examples and boundary cases,
- v3.0.3 package version alignment.

## Results

| Check | Result |
| --- | --- |
| `uv run --extra dev pytest -q` | Passed: 412 tests |
| `uv run --extra dev pytest tests/test_commercial_surfaces.py tests/test_schema_cmd.py -q` | Passed: 43 tests |
| `uv run --extra dev ruff check .` | Passed |
| `uv run --extra dev ruff format --check .` | Passed |
| Starter kit smoke: `init --template team-standard` then `doctor --fail-under 80 --format json` | Passed: adopter score 90, status `strong` |
| `skills-orchestrator schema validate --kind doctor --input doctor.json` on starter kit smoke output | Passed |
| Registry diff Markdown smoke with owner/source/version/content changes | Passed: Markdown lists reviewer-facing field changes |
| `uv run --extra dev python -m build` | Passed: wheel and sdist built for 3.0.3 |
| `uv run --extra dev twine check dist/*` | Passed |
| Wheel smoke install with Python 3.12 | Passed: `skills-orchestrator --version` returned 3.0.3 and starter kit doctor/schema validation passed |
| `uv run --with pip-audit==2.10.1 pip-audit --strict --requirement constraints.txt` | Passed: no known vulnerabilities |

## Notes

The default doctor profile now reflects adopter readiness. Maintainer-only release artifacts such as
`action.yml`, `Dockerfile`, and this versioned test report are checked only with
`doctor --profile maintainer`.

The package still declares `requires-python = ">=3.12"`. macOS users running the system Python 3.9
must install with an explicit Python 3.12 interpreter, pipx, uvx, or Docker.
