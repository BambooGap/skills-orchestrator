# Policy Packs

Policy packs are the team-level contract that turns skill authoring rules into repeatable checks.

The current release enforces built-in diagnostics through `skills-orchestrator check`. A future
policy-pack runtime should make these rules configurable by organization, but teams can already use
this document as the review contract.

## Current Enforceable Surface

```bash
skills-orchestrator check --config config/skills.yaml --fail-on warning
skills-orchestrator check --config config/skills.yaml --check-lock skills.lock.json
```

Current diagnostics cover required metadata, duplicate IDs, conflict declarations, oversized skill
files, config drift, and lock drift.

## Recommended Team Pack

A team-standard pack should require:

- `id`, `name`, `summary`, and explicit `load_policy` in every skill.
- `owner` and `approved_by` frontmatter for required skills.
- `version` or release note linkage for shared skills.
- `source` for imported skills.
- `conflict_with` review when skills target the same runtime behavior.
- `skills.lock.json` regeneration when content hashes change.
- Manifest and policy export evidence for protected branches or releases.

## Frontmatter Shape

```yaml
---
id: team-review
name: Team Review
summary: Shared review rules for production changes.
tags: [review, team]
load_policy: require
owner: platform-team
approved_by: security-review
version: 1.4.0
source: internal
---
```

Fields beyond the current core schema are safe to keep in source-controlled frontmatter, but they
are not yet enforced unless your team adds a local checker around the JSON manifest.

## Versioning Rules

- Treat required skills as versioned team assets.
- Review required skill changes like code changes.
- Regenerate `skills.lock.json` after content or metadata changes.
- Keep generated artifacts either committed everywhere or generated in CI everywhere.

## Migration Path

1. Start with `check --fail-on warning`.
2. Add `skills.lock.json` to PR review.
3. Export the native manifest in CI.
4. Add a local manifest checker for owner/version fields if your organization needs them now.
5. Move to built-in `policy_packs` when the runtime is added.
