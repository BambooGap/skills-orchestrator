# Ecosystem Adapters

Adapters are bridge contracts for adjacent agent ecosystems. They do not replace the native
manifest, resolver, or MCP runtime.

## Inspect A Repository

```bash
skills-orchestrator adapters inspect --path . --format json > adapter-inspect.json
skills-orchestrator schema validate --kind adapter-inspect --input adapter-inspect.json
```

Detected surfaces:

- `agents-md`: existing `AGENTS.md` bootstrap output.
- `claude-skills`: Claude-style `*/SKILL.md` bundle entrypoints under `.claude/skills` or
  `.agents/skills`.
- `mcp-client-config`: existing MCP client configuration files.
- `openai-agents-sdk`: Python or TypeScript Agents SDK dependencies.

Claude Skills detection only treats `SKILL.md` as a skill entrypoint. Supporting files such as
references, examples, and scripts remain assets inside that skill bundle.

## Export MCP Client Config

```bash
skills-orchestrator adapters export mcp-client-config \
  --config config/skills.yaml \
  --output mcp-client.json
```

The generated config uses an absolute `--config` path so the stdio server can start from any client
working directory.

## Export OpenAI Agents SDK Scaffold

```bash
skills-orchestrator adapters export openai-agents-sdk \
  --config config/skills.yaml \
  --output openai_skillops_agent.py
```

The scaffold shows how to attach the existing Skills Orchestrator MCP server through
`MCPServerStdio`. It does not call a model, create an agent workflow, or claim a project-level
auto-discovery standard.
