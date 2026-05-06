# Test Report v2.0.5

- **Commit:** bab2eac688328046490e51976580ad8741ea62ec
- **Tag:** v2.0.5
- **Python Version:** Python 3.12.10
- **OS:** Darwin 25.3.0 arm64
- **Test Time:** 2026-05-07 00:16:30 CST

## Commands

| Command | Result |
|---------|--------|
| `pytest tests/ -q` | Passed: 288 tests |
| `ruff check .` | Passed |
| `ruff format --check .` | Passed: 51 files already formatted |
| `python -m build` | Passed: built `skills_orchestrator-2.0.5.tar.gz` and `skills_orchestrator-2.0.5-py3-none-any.whl` |
| `twine check dist/skills_orchestrator-2.0.5*` | Passed |
| `skills-orchestrator --help` | Passed |
| `skills-orchestrator init --help` | Passed |
| `skills-orchestrator mcp-test --help` | Passed |
| `skills-orchestrator --version` | Passed: `skills-orchestrator, version 2.0.5` |

## Result

Passed. v2.0.5 hardens MCP and Pipeline path handling, validates user-controlled identifiers, improves keyword search caching, replaces recursive Pipeline auto-skip with an iterative loop, and adds Windows console/subprocess encoding compatibility.

## Stress Checks

| Scenario | Result |
|----------|--------|
| 5000 skills parse | Passed: 1.226s |
| 5000 skills registry load | Passed: 1.203s |
| Cold search top20 | Passed: 0.052s |
| 40 warm searches | Passed: 0.478s |
| 160 concurrent searches across 8 workers | Passed: 2.465s |
| 1200-step Pipeline auto-skip | Passed: 0.003s |
| Save 1500 large RunState files | Passed: 4.405s |
| List 1500 large RunState files | Passed: 1.357s |

## Failed Cases

None.

## Notes

- MCP inputs now reject path traversal and malformed non-object arguments.
- Pipeline run state paths now validate `pipeline_id`, `run_id`, and `.latest` references.
- Windows GBK terminals receive ASCII fallbacks for CLI status glyphs and unencodable emoji.
- Subprocess text decoding now explicitly uses UTF-8 with replacement.
