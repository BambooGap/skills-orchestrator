# Ecosystem Adapters

Adapters are bridge contracts for adjacent agent ecosystems. They do not replace the native
manifest, resolver, or MCP task-scoped loading surface.

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

## Export Claude Skills Bundles

```bash
skills-orchestrator adapters export claude-skills \
  --config config/skills.yaml \
  --output-dir .claude/skills \
  --manifest-output claude-skills-export.json
```

The exporter writes one `*/SKILL.md` bundle per SkillOps skill and preserves governance metadata
such as `owner`, `source`, `version`, `license`, review windows, and import `provenance` in
frontmatter. Those bundles can be read back through `skill_dirs` for round-trip fixture tests.

This is a file-format bridge only. It does not call Claude, install Claude Code, or assume runtime
reload semantics.

For a copyable round-trip fixture, see
[`examples/adapter-evidence/`](../examples/adapter-evidence/README.md). It exports Claude Skills
bundles, generates MCP and OpenAI Agents SDK scaffolds, compiles the OpenAI scaffold, and then
produces adapter inspection evidence from the generated files.

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

## Adapter Evidence Fixture

Use the dedicated fixture when you need a reproducible Level 4 conformance example:

```bash
cd examples/adapter-evidence
mkdir -p evidence

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
```

The fixture proves adapter artifact generation and inspection. It deliberately avoids runtime model
calls and API keys.
