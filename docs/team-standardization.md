# Team Standardization Guide

Use Skills Orchestrator as a team control plane for agent instructions:

1. keep skills in source control,
2. check them in CI,
3. lock and review instruction changes,
4. export manifests for audit,
5. export registry/evidence bundles for release review,
6. route runtime context through MCP.

## Repository Contract

A team repository should contain:

```text
config/skills.yaml
config/pipelines/*.yaml
skills/**/*.md
AGENTS.md
skills.lock.json
```

Bootstrap the source files with:

```bash
skills-orchestrator init --template team-standard
skills-orchestrator check --config config/skills.yaml --policy-pack builtin/team-standard
skills-orchestrator build --config config/skills.yaml --lock
```

Generated files such as `AGENTS.md` and `skills.lock.json` may either be committed for review or
generated in CI. Pick one policy and keep it consistent across the organization.

## Ownership Model

Every team should name owners for three surfaces:

| Surface | Owner | Review Responsibility |
| --- | --- | --- |
| `skills/**/*.md` | Domain team | Instruction content, scope, and conflicts. |
| `config/skills.yaml` | Platform or repo owner | Zones, load policies, and team defaults. |
| CI / release artifacts | Release owner | SARIF upload, lock drift, manifest, policy exports. |

Required skills should have explicit owner/source/version/lifecycle and approvers in frontmatter.
`builtin/team-standard` enforces that contract.

## Required CI Gate

Use the GitHub Action for the normal check gate:

```yaml
permissions:
  contents: read
  security-events: write

jobs:
  skills:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: BambooGap/skills-orchestrator@v3.0.6
        with:
          config: config/skills.yaml
          check-lock: skills.lock.json
          policy-pack: builtin/team-standard
          upload-sarif: true
```

Teams that do not use GitHub Code Scanning can run the same gate without SARIF upload:

```bash
skills-orchestrator check \
  --config config/skills.yaml \
  --check-lock skills.lock.json \
  --policy-pack builtin/team-standard \
  --fail-on warning
```

## Review Contract

Treat skill changes like code changes. A reviewer should check:

- frontmatter includes `id`, `name`, `summary`, and intentional `load_policy`,
- shared or required skills have `owner`, `source`, `version`, `lifecycle`, and required-skill
  `approvers`,
- required skills are narrowly scoped,
- `conflict_with` is symmetrical unless the one-way relation is intentional,
- lock drift is either regenerated or explicitly rejected,
- generated manifest and policy exports still describe the expected active zone.

## Generated File Policy

Choose one organization-wide mode:

- Commit generated files: `AGENTS.md`, `skills.lock.json`, and selected manifests are reviewed in
  pull requests.
- Generate in CI: generated files are artifacts only, and PRs must pass the check job.

Mixing both modes across repos makes review and rollback harder.

## Audit Artifacts

Generate these artifacts for release or internal audit:

```bash
skills-orchestrator evidence export \
  --config config/skills.yaml \
  --policy-pack builtin/team-standard \
  --out evidence
```

The native JSON manifest is the authoritative instruction inventory. CycloneDX is an experimental
adapter for existing supply-chain vocabulary. OPA/Rego exports are proof fixtures, not a second
runtime policy engine. `evidence export` writes all of these plus doctor and registry artifacts.

## Runtime Contract

When MCP is enabled, teams should put one stable instruction in `AGENTS.md`:

```text
For every new task or major task change, call prepare_context(task) first.
Follow only active_skills for the current task. Treat previously loaded skills that are not
returned as inactive for this task.
```

This keeps old instructions from silently carrying into unrelated tasks.

Enable runtime audit when a team needs usage evidence. For commercial logs, set an audit salt so
task hashes use HMAC-SHA256:

```bash
export SKILLS_ORCHESTRATOR_AUDIT_SALT="$(openssl rand -hex 32)"
skills-orchestrator serve --config config/skills.yaml --audit-dir .skills-audit
skills-orchestrator usage report --audit-dir .skills-audit
```

The audit log stores routing hashes and skill IDs, not raw task text or skill content.

## Rollout Sequence

1. Start with `check --format text` locally.
2. For new repos, run `init --template team-standard`; for existing repos, run
   `init --non-interactive`.
3. Add the GitHub Action without SARIF upload.
4. Generate and review `skills.lock.json`.
5. Enable `builtin/team-standard` without `--fail-on warning`; fix governance metadata.
6. Turn on SARIF upload when repository permissions allow `security-events: write`.
7. Add `doctor --profile adopter`, `registry build`, `registry diff --format markdown`,
   `schema validate`, and `evidence export` to release evidence.
8. Enable MCP for runtime routing after CI is stable.

## Acceptance Criteria

A repository is team-standardized when:

- `check --policy-pack builtin/team-standard --fail-on warning` passes in CI,
- lock drift is reviewed or blocked,
- SARIF is uploaded where Code Scanning is enabled,
- release evidence includes an `evidence export` bundle and registry snapshot,
- `doctor --profile adopter` meets the team's score threshold,
- runtime MCP usage has a documented audit policy,
- rollback is clear: revert the skill/config change and regenerate affected artifacts.
