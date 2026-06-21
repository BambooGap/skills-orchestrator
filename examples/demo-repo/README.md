# SkillOps Demo Repository

This directory is a runnable demo for SkillOps Contract v1. It is designed to be copied into a
standalone repository or executed in place from the repository root.

It demonstrates:

- skill metadata validation,
- team policy checks,
- SARIF output,
- registry build and diff,
- PR comment body generation,
- evidence bundle export,
- adapter inspection for AGENTS.md, Claude Skills, MCP config, and OpenAI Agents SDK.

## Run Locally

From this directory:

```bash
python3.12 -m pip install skills-orchestrator

skills-orchestrator schema validate --kind config --input config/skills.yaml
skills-orchestrator check \
  --config config/skills.yaml \
  --policy-pack builtin/team-standard \
  --fail-on warning
```

Generate evidence:

```bash
mkdir -p evidence

skills-orchestrator check --config config/skills.yaml --format sarif \
  > evidence/check.sarif

skills-orchestrator registry build \
  --config-glob config/skills.yaml \
  --output evidence/registry-before.json

cp evidence/registry-before.json evidence/registry-after.json

skills-orchestrator registry diff \
  evidence/registry-before.json \
  evidence/registry-after.json \
  --format json \
  --output evidence/registry-diff.json

skills-orchestrator registry diff \
  evidence/registry-before.json \
  evidence/registry-after.json \
  --format markdown \
  --output evidence/registry-diff.md

skills-orchestrator registry comment-body \
  evidence/registry-diff.md \
  --output evidence/registry-diff-comment.md

skills-orchestrator evidence export --config config/skills.yaml --out evidence

skills-orchestrator adapters inspect --path . --format json \
  > evidence/adapter-inspect.json

skills-orchestrator schema validate --kind registry --input evidence/registry-before.json
skills-orchestrator schema validate --kind registry-diff --input evidence/registry-diff.json
skills-orchestrator schema validate --kind evidence --input evidence/evidence-manifest.json
skills-orchestrator schema validate --kind adapter-inspect --input evidence/adapter-inspect.json
```

## Pull Request Demo

To demonstrate a real review flow:

1. Commit this directory as a standalone repository.
2. Create a branch.
3. Change `skills/release-checklist.md`, for example by bumping `version`.
4. Open a pull request.
5. The workflow in `.github/workflows/skillops.yml` runs the action, uploads SARIF, and posts a
   registry diff comment when `pull-requests: write` is available.

## Expected Adapter Surfaces

`skills-orchestrator adapters inspect --path . --format json` should detect:

- `agents-md`
- `claude-skills`
- `mcp-client-config`
- `openai-agents-sdk`

This demo intentionally keeps the OpenAI Agents SDK dependency in `pyproject.toml` so adapter
inspection can verify the dependency surface without running a model call.
