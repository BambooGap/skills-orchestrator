# Test Report v2.1.0

- **Commit:** ebcfcee7d746cf3550e7c8b04228ba7ef1403788
- **Tag:** v2.1.0
- **Python Version:** Python 3.12.10
- **OS:** Darwin 25.3.0 arm64
- **Test Time:** 2026-05-07 22:32:58 CST

## Commands

| Command | Result |
|---------|--------|
| `pytest tests/ -q` | Passed: 312 tests |
| `ruff check .` | Passed |
| `ruff format --check .` | Passed: 52 files already formatted |
| `python -m build` | Passed: built `skills_orchestrator-2.1.0.tar.gz` and `skills_orchestrator-2.1.0-py3-none-any.whl` |
| `twine check dist/skills_orchestrator-2.1.0*` | Passed |
| `python -m skills_orchestrator.main --help` | Passed |
| `python -m skills_orchestrator.main init --help` | Passed |
| `python -m skills_orchestrator.main mcp-test --help` | Passed |
| `python -m skills_orchestrator.main --version` | Passed: `skills-orchestrator, version 2.1.0` |
| `python -m skills_orchestrator.main mcp-test prepare_context '{"task":"做安全审查","max_skills":3,"include_content":false}' -c config/skills.yaml` | Passed |

## Result

Passed. v2.1.0 adds MCP runtime skill routing through `prepare_context` and updates generated `AGENTS.md` files with the task-boundary loading protocol.

## Failed Cases

None.

## Notes

- v2.1.0 adds runtime skill routing through MCP `prepare_context`.
- Generated `AGENTS.md` now documents the per-task runtime loading protocol.
