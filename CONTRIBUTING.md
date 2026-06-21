# Contributing

Skills Orchestrator is an early-stage open-source project. Contributions should improve the
machine-checkable SkillOps contract, CLI behavior, documentation, tests, or examples.

## Development Setup

```bash
git clone https://github.com/BambooGap/skills-orchestrator
cd skills-orchestrator
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install -e ".[dev]" -c constraints.txt
pytest tests/ -v --tb=short
ruff check skills_orchestrator/ tests/
ruff format --check skills_orchestrator/ tests/
```

## Pull Request Expectations

- Keep changes scoped to one concern.
- Include tests for behavior changes.
- Update docs and examples when CLI behavior, schemas, action inputs, or artifact contracts change.
- Explain compatibility impact for changes to `SPEC.md`, JSON Schemas, action inputs, or CLI output
  formats.
- Do not add adopter claims, foundation claims, or governance claims without public evidence.

## Skill Contributions

Skill files are Markdown files with frontmatter. Shared team skills should include governance
metadata accepted by `builtin/team-standard`.

```markdown
---
id: your-skill-id
name: Skill Display Name
summary: Short description for reports and search.
tags: [review, ci]
load_policy: free
priority: 80
zones: [default]
conflict_with: []
owner: platform-team
source: repo://skills/your-skill-id.md
version: 1.0.0
lifecycle: active
---
# Skill Body
```

Before opening a PR:

```bash
skills-orchestrator check \
  --config config/skills.yaml \
  --policy-pack builtin/team-standard \
  --fail-on warning
```

## Contract Contributions

Contract changes should update the executable path, not only prose:

- `SPEC.md`
- `CONFORMANCE.md`
- schema files under `skills_orchestrator/schemas/`
- tests under `tests/`
- runnable examples under `examples/`

Breaking changes should introduce a new contract or schema version.

## Commit Style

Use clear, conventional prefixes when practical:

- `feat:`
- `fix:`
- `docs:`
- `test:`
- `refactor:`

## Governance

See [GOVERNANCE.md](GOVERNANCE.md) and [MAINTAINERS.md](MAINTAINERS.md). The project is currently
single-maintainer and does not claim foundation governance or a public adopter program.
