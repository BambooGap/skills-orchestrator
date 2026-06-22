---
id: plugin-release-gate
name: Plugin Release Gate
summary: Review CI plugin release changes for compatibility, provenance, and versioning.
tags: [release, plugin, ci]
load_policy: free
priority: 80
zones: [default]
conflict_with: []
owner: release-team
source: repo://examples/pilot-repos/woodpecker/skills/plugin-release-gate.md
version: 1.0.0
lifecycle: active
reviewed_at: 2026-06-22
expires_at: 2026-12-22
license: MIT
---
# Plugin Release Gate

Use this skill when a CI plugin release or dependency update changes runtime behavior.

## Checklist

- Confirm plugin versioning follows the repository release policy.
- Verify dependency provenance is visible in the release notes.
- Check backward compatibility for existing pipeline users.
- Require a smoke test that exercises the plugin entrypoint.
