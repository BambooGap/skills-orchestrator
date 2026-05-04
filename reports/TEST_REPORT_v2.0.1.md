# Test Report v2.0.1

- **Commit:** f9b21b50d8eddb968d4775b944158044e684d156
- **Tag:** v2.0.1
- **Python Version:** 3.13.13
- **OS:** macOS 15.3 (arm64)
- **Test Time:** 2026-05-04

## Commands & Results

| Command | Result |
|---------|--------|
| `pytest tests/ -v` | ✅ 185 passed in 1.82s |
| `ruff check .` | ✅ All checks passed |
| `ruff format --check .` | ✅ All formatted |
| `python -m build` | ✅ sdist + wheel built |
| `skills-orchestrator --help` | ✅ OK |
| `skills-orchestrator init --help` | ✅ OK |
| `skills-orchestrator pipeline --help` | ✅ OK |
| `skills-orchestrator mcp-test --help` | ✅ OK |

## Failed Cases

None.

## Notes

- v2.0.1 是 bugfix 发布，修复了 Claude Code 和 Codex 交叉测试发现的 8 个问题
- CI 矩阵：Python 3.12 / 3.13 全通过
- PyPI 发布：OIDC Trusted Publishing 自动完成
