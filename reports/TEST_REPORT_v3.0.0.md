# Test Report v3.0.0

Date: 2026-06-21

## Scope

Validated the v3.0.0 open-core release slice:

- registry diff PR comment automation,
- package SBOM generation,
- CodeQL and GHCR workflows,
- ecosystem adapter inspection and scaffolds,
- commercial handoff schemas and examples,
- v3.0.0 package build.

## Results

| Check | Result |
| --- | --- |
| `uv run --extra dev pytest -q` | Passed: 409 tests |
| `uv run --extra dev ruff check skills_orchestrator tests scripts/check_action_pins.py` | Passed |
| `uv run --extra dev ruff format --check skills_orchestrator tests scripts/check_action_pins.py` | Passed |
| `uv run --extra dev python scripts/check_action_pins.py` | Passed |
| `uv run --extra dev skills-orchestrator build --config config/skills.yaml --output AGENTS.md` | Passed |
| `uv run --extra dev skills-orchestrator adapters inspect --format json` | Passed |
| `uv run --extra dev skills-orchestrator supply-chain sbom --no-dependencies` | Passed |
| Commercial handoff schema validation | Passed |
| `uv run --with pip-audit==2.10.1 pip-audit --strict --requirement constraints.txt` | Passed after constraints refresh |
| `python3.12 -m venv /tmp/skills-orchestrator-constraints-smoke && pip install -c constraints.txt -e .` | Passed |
| `uv run --extra dev python -m build` | Passed |
| `uv run --extra dev twine check dist/*` | Passed |
| Wheel smoke install from `dist/skills_orchestrator-3.0.0-py3-none-any.whl` | Passed |

## Notes

`pip-audit` initially reported vulnerabilities in constrained transitive dependencies. The
constraints file was refreshed to patched versions and the audit was rerun successfully.

GHCR publishing and CodeQL execution are workflow-level checks. They are expected to run on GitHub
after this branch is pushed and the pull request is opened.

Code and security review blockers were fixed before final verification:

- PR comment upsert now only updates marker comments authored by allowed bot accounts.
- Package SBOM dependency enumeration skips optional extras by default.
- Adapter inspection now parses Claude skill frontmatter and MCP JSON before reporting a surface as
  detected.
- Commercial handoff schemas now restrict GitHub App permissions/events and hosted artifact paths.
