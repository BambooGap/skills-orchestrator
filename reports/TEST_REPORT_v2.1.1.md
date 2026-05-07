# Test Report v2.1.1

- **Commit:** 5ba8dc59b22507ac14f532afb7078fcb6e789668
- **Tag:** v2.1.1
- **Python Version:** Python 3.12.10
- **OS:** Darwin 25.3.0 arm64
- **Test Time:** 2026-05-07 23:19:25 CST

## Commands

| Command | Result |
|---------|--------|
| `pytest tests/ -q` | Passed: 313 tests |
| `ruff check .` | Passed |
| `ruff format --check .` | Passed: 52 files already formatted |
| `python -m build` | Passed: built `skills_orchestrator-2.1.1.tar.gz` and `skills_orchestrator-2.1.1-py3-none-any.whl` |
| `twine check dist/skills_orchestrator-2.1.1*` | Passed |
| `python -m skills_orchestrator.main --version` | Passed: `skills-orchestrator, version 2.1.1` |
| `python -m skills_orchestrator.main mcp-test prepare_context '{"task":"实现快速排序","max_skills":1,"include_content":false}' -c config/skills.yaml` | Passed: required skills present in active_skills |

## Result

Passed. v2.1.1 fixes a governance hole in `prepare_context` and corrects a misleading field name.

## Fixed Cases

- **prepare_context forced-first**: required/forced skills now unconditionally enter `active_skills` regardless of task relevance score. `max_skills` limits only task-relevant passive skills. Previously, a forced skill (e.g., enterprise security-check) could be displaced by unrelated passive skills with higher keyword scores.
- **inactive_skills rename**: `inactive_previous_skills` renamed to `inactive_skills`. The old name implied the skills were loaded in a previous turn; the field actually lists skills not selected for the current task (the tool is stateless).

## Failed Cases

None.

## Notes

- New test `test_prepare_context_required_skills_always_in_active` verifies the forced-first guarantee end-to-end.
- `SkillRegistry` gains `forced()` and `passive()` public methods for callers that need to distinguish required from optional skills.
