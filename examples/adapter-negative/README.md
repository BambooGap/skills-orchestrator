# Adapter Negative Fixtures

This example contains intentionally malformed adapter surfaces. It exists so platform teams and
third-party implementers can verify that adapter detection is conservative and artifact-driven.

It covers:

- Claude Skills directories where `*/SKILL.md` is present but malformed or missing required
  frontmatter fields,
- MCP client config files that are not valid JSON,
- OpenAI-looking project files that do not declare a supported Agents SDK dependency.

## Run

From this directory:

```bash
mkdir -p evidence

skills-orchestrator adapters inspect --path . --format json \
  > evidence/adapter-inspect.json

skills-orchestrator schema validate \
  --kind adapter-inspect \
  --input evidence/adapter-inspect.json
```

## Expected Result

`evidence/adapter-inspect.json` should be schema-valid, but these surfaces should remain
undetected:

- `claude-skills`
- `mcp-client-config`
- `openai-agents-sdk`

The Claude Skills surface should report invalid entrypoints under `verification.invalid_paths`,
and the MCP surface should report `.mcp.json` as invalid. Supporting files that are not
`*/SKILL.md` entrypoints must not be treated as skills.
