# Policy Packs

Policy packs turn team skill-authoring rules into repeatable checks.

`v3.0.0` and later include the built-in pack:

```bash
skills-orchestrator check \
  --config config/skills.yaml \
  --policy-pack builtin/team-standard
```

Use `--fail-on warning` when the team is ready to make the contract blocking:

```bash
skills-orchestrator check \
  --config config/skills.yaml \
  --policy-pack builtin/team-standard \
  --fail-on warning
```

## `builtin/team-standard`

This pack adds governance diagnostics:

| Rule | Severity | Requirement |
| --- | --- | --- |
| `SO008` | warning | every skill should have `owner` |
| `SO009` | warning | every skill should have `source` |
| `SO010` | warning | every skill should have `version` |
| `SO011` | error | `lifecycle` must be `active`, `beta`, `deprecated`, or `retired` |
| `SO012` | warning | required skills should have `approvers` |

## Frontmatter Shape

```yaml
---
id: team-review
name: Team Review
summary: Shared review rules for production changes.
tags: [review, team]
load_policy: require
owner: platform-team
source: internal://agent-skills/team-review
version: 1.4.0
lifecycle: active
approvers: [security-review, staff-engineering]
---
```

These fields are exported in:

- native instruction manifests,
- experimental CycloneDX properties,
- OPA input policy export,
- organization registry snapshots.

## GitHub Action

```yaml
- uses: BambooGap/skills-orchestrator@v3.0.2
  with:
    config: config/skills.yaml
    policy-pack: builtin/team-standard
    fail-on: warning
```

For SARIF upload, also set `upload-sarif: true` and grant `security-events: write`.

## Migration Path

1. Run the pack without `--fail-on warning` and review findings.
2. Add `owner`, `source`, `version`, and `lifecycle` to every shared skill.
3. Add `approvers` to required skills.
4. Regenerate `skills.lock.json`.
5. Turn on `--fail-on warning` in protected branch CI.
6. Add `doctor` and `evidence export` to release verification.
