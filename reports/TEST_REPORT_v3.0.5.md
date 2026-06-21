# Test Report v3.0.5

Date: 2026-06-21

## Scope

Validated the v3.0.5 contract patch for the issues found in external retests:

- YAML null governance metadata no longer becomes the literal string `"None"`;
- invalid skill `load_policy` is reported as structured `SO013` in text, JSON, and SARIF;
- explicit `skills[].path` entries in `config/skills.yaml` resolve from the project root;
- explicit missing skill files keep `missing_file=true` while existing files are not misreported;
- `SPEC.md` documents the `missing_file` boundary between explicit paths and `skill_dirs` discovery.

## Commands

```bash
uv run --extra dev pytest tests/test_parser.py::test_explicit_skill_path_from_config_dir_cannot_escape_project_root tests/test_parser.py::test_explicit_skill_path_outside_project_rejected tests/test_parser.py::test_skill_dirs_skills_root_allowed tests/test_security.py tests/test_main_cli.py::test_check_reports_invalid_frontmatter_load_policy_with_skill_location tests/test_policy_packs.py::test_team_standard_policy_pack_treats_null_governance_as_missing tests/test_commercial_surfaces.py::test_registry_explicit_skill_paths_resolve_from_project_root -q
uv run --extra dev pytest -q
uv run --extra dev ruff check .
uv run --extra dev ruff format --check .
uv run --with pip-audit==2.10.1 pip-audit --strict --requirement constraints.txt
rm -rf dist && uv run --extra dev python -m build && uv run --extra dev twine check dist/*
```

## Results

- Targeted parser/security/diagnostic tests: `19 passed`
- Full test suite: `417 passed`
- Ruff check: passed
- Ruff format check: passed
- pip-audit: no known vulnerabilities found
- Package build: produced `skills_orchestrator-3.0.5.tar.gz` and `skills_orchestrator-3.0.5-py3-none-any.whl`
- Twine package validation: passed for both artifacts

## Wheel Smoke

Installed the locally built wheel into a clean Python 3.12 virtual environment and verified:

- `skills-orchestrator --version` reports `3.0.5`;
- `pipeline list` loads packaged pipeline resources outside the source tree;
- `registry build` on a `config/skills.yaml` explicit-path project marks existing files as `missing_file=false` and missing explicit files as `missing_file=true`;
- `schema validate --kind registry --input <registry.json>` passes;
- `check --format json` reports invalid frontmatter `load_policy` as `SO013` with the skill-relative file path.

## Security Diff Scan

Used the Codex Security diff-scan workflow in terminal fallback mode. Capability preflight returned `status=ready`.

Reviewed changed security-sensitive surfaces:

- `skills_orchestrator/compiler/parser.py`
- `skills_orchestrator/checker.py`
- `skills_orchestrator/diagnostic.py`
- path and metadata regression tests

Findings:

- No path traversal regression found. Explicit paths from `config/skills.yaml` are normalized against the computed project root and still go through `validate_path_within_root`.
- Added a regression test proving `config/skills.yaml` cannot escape the project root with `../outside.md`.
- `SO013` reports relative skill paths for frontmatter diagnostics, avoiding leakage of absolute local workspace paths in normal CI output.
- No new subprocess, network, credential, token, or shell execution surface was introduced.

Limitation: additional delegated security reviewer spawning was unavailable because the current Codex thread had reached its sub-agent limit. The scan was completed in the parent thread using the plugin's terminal fallback path.

