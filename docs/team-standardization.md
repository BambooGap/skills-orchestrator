# Team Standardization Guide

Use Skills Orchestrator as a team control plane for agent instructions:

1. keep skills in source control,
2. check them in CI,
3. lock and review instruction changes,
4. export manifests for audit,
5. route runtime context through MCP.

## Repository Contract

A team repository should contain:

```text
config/skills.yaml
config/pipelines/*.yaml
skills/**/*.md
AGENTS.md
skills.lock.json
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

Required skills should have an explicit owner and reviewer in frontmatter, even before built-in
policy packs enforce those fields.

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
      - uses: BambooGap/skills-orchestrator@v2.4.0
        with:
          config: config/skills.yaml
          check-lock: skills.lock.json
          upload-sarif: true
```

Teams that do not use GitHub Code Scanning can run the same gate without SARIF upload:

```bash
skills-orchestrator check --config config/skills.yaml --check-lock skills.lock.json
```

## Review Contract

Treat skill changes like code changes. A reviewer should check:

- frontmatter includes `id`, `name`, `summary`, and intentional `load_policy`,
- shared or required skills have an owner and approval trail,
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
skills-orchestrator manifest --config config/skills.yaml --format json \
  --output instruction-manifest.json

skills-orchestrator manifest --config config/skills.yaml --format cyclonedx \
  --output instruction-manifest.cdx.json

skills-orchestrator policy export --config config/skills.yaml --format opa-input \
  --output policy-input.json
```

The native JSON manifest is the authoritative instruction inventory. CycloneDX is an experimental
adapter for existing supply-chain vocabulary. OPA/Rego exports are proof fixtures, not a second
runtime policy engine.

## Runtime Contract

When MCP is enabled, teams should put one stable instruction in `AGENTS.md`:

```text
For every new task or major task change, call prepare_context(task) first.
Follow only active_skills for the current task. Treat previously loaded skills that are not
returned as inactive for this task.
```

This keeps old instructions from silently carrying into unrelated tasks.

Enable runtime audit when a team needs usage evidence:

```bash
skills-orchestrator serve --config config/skills.yaml --audit-dir .skills-audit
skills-orchestrator usage report --audit-dir .skills-audit
```

The audit log stores routing hashes and skill IDs, not raw task text or skill content. Task hashes
are deterministic pseudonymous identifiers and can be correlated across logs.

## Rollout Sequence

1. Start with `check --format text` locally.
2. Add the GitHub Action without SARIF upload.
3. Generate and review `skills.lock.json`.
4. Turn on SARIF upload when repository permissions allow `security-events: write`.
5. Add manifest and policy exports to release evidence.
6. Enable MCP for runtime routing after CI is stable.

## Acceptance Criteria

A repository is team-standardized when:

- `check --fail-on warning` passes in CI,
- lock drift is reviewed or blocked,
- SARIF is uploaded where Code Scanning is enabled,
- release evidence includes manifest and policy exports,
- runtime MCP usage has a documented audit policy,
- rollback is clear: revert the skill/config change and regenerate affected artifacts.
