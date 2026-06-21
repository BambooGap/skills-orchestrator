# Test Report v3.0.4

Date: 2026-06-21

## Scope

Validated the v3.0.4 contract patch:

- `registry diff` changed-entry JSON now validates against `registry-diff.schema.json`,
- changed registry diffs have regression coverage,
- installed wheels include built-in pipeline templates,
- `pipeline list` works outside a source checkout,
- package metadata and user-facing install examples point to v3.0.4.

## Results

| Check | Result |
| --- | --- |
| `uv run --extra dev pytest -q` | Passed: 413 tests |
| `uv run --extra dev pytest tests/test_commercial_surfaces.py tests/test_schema_cmd.py tests/test_e2e.py::TestE2ECLIIntegration::test_pipeline_list -q` | Passed: 45 tests |
| `uv run --extra dev ruff check .` | Passed |
| `uv run --extra dev ruff format --check .` | Passed |
| Changed registry diff smoke: build base/head, change `release-checklist` version, run `schema validate --kind registry-diff` | Passed |
| Fresh wheel install smoke with Python 3.12 outside source checkout | Passed: `skills-orchestrator --version` returned 3.0.4 |
| Installed wheel `pipeline list` smoke outside source checkout | Passed: listed `full-dev`, `quick-fix`, and `review-only` built-in pipelines |
| Installed wheel changed registry diff smoke | Passed: `schema validate --kind registry-diff --input diff.json` |
| `uv run --extra dev python -m build` | Passed: wheel and sdist built for 3.0.4 |
| `uv run --extra dev twine check dist/*` | Passed |
| `uv run --with pip-audit==2.10.1 pip-audit --strict --requirement constraints.txt` | Passed: no known vulnerabilities |
| `git diff --check` | Passed |

## Notes

The `changed[].skill` field in registry diff output is intentionally a compact reviewer snapshot, not
the full registry skill object. The schema now models that contract directly, and regression coverage
validates the generated changed diff JSON against the schema.

Built-in pipeline templates are now packaged under `skills_orchestrator/config/pipelines/` so installed
wheels do not depend on a source checkout layout.
