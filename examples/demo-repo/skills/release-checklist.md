---
id: release-checklist
name: Release Checklist
summary: Verify SkillOps evidence before tagging or publishing a release.
tags: [release, evidence, supply-chain]
load_policy: require
priority: 100
zones: [default]
conflict_with: []
owner: release-team
source: repo://examples/demo-repo/skills/release-checklist.md
version: 1.0.0
lifecycle: active
approvers: [release-team]
reviewed_at: 2026-06-21
expires_at: 2026-12-21
license: MIT
---
# Release Checklist

Use this skill before tagging a release.

## Required Evidence

- `check.json` and `check.sarif` were generated from the current commit.
- `skill-registry.json` was generated and reviewed.
- `registry-diff.md` was reviewed for unexpected skill additions, removals, or metadata changes.
- `evidence/evidence-manifest.json` validates against the evidence schema.
- Adapter inspection output validates against the adapter inspection schema.

## Output

Write a short go/no-go release note with links or paths to the evidence files.
