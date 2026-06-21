# Test Report v3.0.1

Date: 2026-06-21

## Scope

Validated the v3.0.1 technical credibility patch:

- SkillOps Contract v1 documentation,
- conformance checks documentation,
- security policy and reporting boundary,
- runnable demo repository fixture,
- GitHub Action Marketplace branding metadata,
- minimal honest governance and maintainer files,
- v3.0.1 package version alignment.

## Results

| Check | Result |
| --- | --- |
| `uv run --extra dev pytest -q` | Passed: 409 tests |
| `uv run --extra dev ruff check skills_orchestrator tests scripts/check_action_pins.py` | Passed |
| `uv run --extra dev ruff format --check skills_orchestrator tests scripts/check_action_pins.py` | Passed |
| `uv run --extra dev python scripts/check_action_pins.py` | Passed |
| `git diff --check` | Passed |
| Demo repo config schema validation | Passed |
| Demo repo `builtin/team-standard` check | Passed |
| Demo repo SARIF generation | Passed |
| Demo repo registry build, JSON diff, Markdown diff, and PR comment body generation | Passed |
| Demo repo evidence bundle export and schema validation | Passed |
| Demo repo adapter inspection with AGENTS.md, Claude Skills, MCP config, and OpenAI Agents SDK surfaces | Passed |
| CI demo repo adapter surface assertion | Passed locally: expected surfaces detected 4/4 |
| `uv run --extra dev python -m build` | Passed: wheel and sdist built for 3.0.1 |
| `uv run --extra dev twine check dist/*` | Passed |
| `uv run --with pip-audit==2.10.1 pip-audit --strict --requirement constraints.txt` | Passed: no known vulnerabilities |
| Wheel smoke install with Python 3.12 | Passed: `skills-orchestrator --version` returned 3.0.1 and demo config schema validation passed |

## Notes

No new CLI behavior was added in this patch. The release is intended to make the existing v3.0.x
artifact contracts easier for external engineering teams to evaluate and reproduce.

The first wheel smoke attempt used the system `python3` binary, which is Python 3.9.6 on this host
and is below the declared `>=3.12` requirement. The smoke was rerun with `python3.12` and passed.
