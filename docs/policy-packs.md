# Policy Packs

Policy packs turn team skill-authoring rules into repeatable checks.

`v3.0.0` and later include the built-in team pack:

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

## `builtin/engineering-grade`

This pack includes `builtin/team-standard` and adds review-window diagnostics:

| Rule | Severity | Requirement |
| --- | --- | --- |
| `SO014` | warning | every shared skill should have `reviewed_at` and `expires_at` |
| `SO015` | error | review-window dates must use `YYYY-MM-DD`, and `expires_at` must be on or after `reviewed_at` |
| `SO016` | error | `expires_at` must not be in the past |

```bash
skills-orchestrator check \
  --config config/skills.yaml \
  --policy-pack builtin/engineering-grade \
  --fail-on warning
```

## Local Declarative Packs

Local packs are safe YAML/JSON data contracts. They do not import Python modules or execute
repository code.

```yaml
schema_version: skills-orchestrator.policy-pack.v1
id: org/enterprise
name: Enterprise SkillOps
rules:
  - id: require-review-window
    severity: error
    required_fields: [reviewed_at, expires_at]
  - id: active-or-beta-only
    severity: warning
    allowed_values:
      - field: lifecycle
        values: [active, beta]
```

Validate and run:

```bash
skills-orchestrator schema validate --kind policy-pack --input policy-pack.yaml
skills-orchestrator check --config config/skills.yaml --policy-pack policy-pack.yaml
```

`required_fields` can target any supported skill metadata field. `allowed_values` is intentionally
limited to scalar fields such as `lifecycle`, `load_policy`, `owner`, `source`, `version`,
`reviewed_at`, and `expires_at`; list fields such as `tags` and `approvers` are not accepted there.

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
reviewed_at: 2026-06-21
expires_at: 2026-12-21
---
```

These fields are exported in:

- native instruction manifests,
- experimental CycloneDX properties,
- OPA input policy export,
- organization registry snapshots,
- conformance reports.

## GitHub Action

```yaml
- uses: BambooGap/skills-orchestrator@v3.1.0
  with:
    config: config/skills.yaml
    policy-pack: builtin/engineering-grade
    fail-on: warning
```

For SARIF upload, also set `upload-sarif: true` and grant `security-events: write`.

## Migration Path

1. Run the pack without `--fail-on warning` and review findings.
2. Add `owner`, `source`, `version`, and `lifecycle` to every shared skill.
3. Add `approvers` to required skills.
4. Add `reviewed_at` and `expires_at` before enabling `builtin/engineering-grade`.
5. Regenerate `skills.lock.json`.
6. Turn on `--fail-on warning` in protected branch CI.
7. Add `doctor --profile adopter`, `conformance run`, and `evidence export` to release verification.
