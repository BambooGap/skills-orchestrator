# Adapter Evidence Example

This example proves that the same SkillOps source config can produce evidence for adjacent agent
ecosystems without adding a runtime dependency to the core CLI.

It covers:

- Claude Skills bundle export with SkillOps governance metadata preserved,
- MCP client config generation,
- OpenAI Agents SDK scaffold generation and syntax compilation,
- adapter inspection evidence for `agents-md`, `claude-skills`, `mcp-client-config`, and
  `openai-agents-sdk`.

## Run

From this directory:

```bash
mkdir -p evidence

skills-orchestrator schema validate --kind config --input config/skills.yaml
skills-orchestrator check \
  --config config/skills.yaml \
  --policy-pack builtin/engineering-grade \
  --fail-on warning

skills-orchestrator build \
  --config config/skills.yaml \
  --output AGENTS.md

skills-orchestrator adapters export claude-skills \
  --config config/skills.yaml \
  --output-dir .claude/skills \
  --manifest-output evidence/claude-skills-export.json \
  --force

skills-orchestrator adapters export mcp-client-config \
  --config config/skills.yaml \
  --output .mcp.json \
  --force

skills-orchestrator adapters export openai-agents-sdk \
  --config config/skills.yaml \
  --output evidence/openai_skillops_agent.py \
  --force

python -m py_compile evidence/openai_skillops_agent.py

skills-orchestrator adapters inspect --path . --format json \
  > evidence/adapter-inspect.json

skills-orchestrator schema validate \
  --kind adapter-inspect \
  --input evidence/adapter-inspect.json
```

## Expected Surfaces

`evidence/adapter-inspect.json` should report these detected surfaces:

- `agents-md`
- `claude-skills`
- `mcp-client-config`
- `openai-agents-sdk`

The OpenAI Agents SDK scaffold is intentionally only compiled. The example does not call a model or
require a runtime API key.
