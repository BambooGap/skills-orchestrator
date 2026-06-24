---
id: adapter-handshake
name: Adapter Handshake
summary: Verify that adjacent agent runtimes consume SkillOps evidence instead of bypassing it.
tags: [adapter, mcp, agent-runtime]
load_policy: free
priority: 80
zones: [default]
conflict_with: []
owner: platform-team
source: repo://examples/adapter-evidence/skills/adapter-handshake.md
version: 1.0.0
lifecycle: active
approvers: [platform-team]
reviewed_at: 2026-06-24
expires_at: 2026-12-24
license: MIT
provenance:
  source_url: https://github.com/BambooGap/skills-orchestrator/blob/main/examples/adapter-evidence/skills/adapter-handshake.md
  source_ref: main
  source_commit: local-fixture
  content_hash: sha256:fixture
  fetched_at: 2026-06-24T00:00:00Z
---
# Adapter Handshake

Use this skill when connecting SkillOps artifacts to an adjacent agent runtime.

## Requirements

- Generate adapter inspection evidence before claiming compatibility.
- Preserve SkillOps metadata when exporting Claude Skills bundles.
- Treat MCP and OpenAI Agents SDK files as scaffolds, not runtime proof.
- Keep model calls and API keys outside the fixture.

## Output

List the generated adapter artifacts and whether each one was validated.

