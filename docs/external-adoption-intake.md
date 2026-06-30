# External Adoption Intake

Use this checklist when a repository outside this project wants to adopt Skills Orchestrator. It is
written for platform teams, security reviewers, and maintainers who need a clear go / no-go decision
before turning SkillOps into a blocking gate. If the repository owner has not approved an adoption yet,
start with [Adoption Authorization](adoption-authorization.md). If the owner closes the request or says
they are not interested, stop there; do not follow up, open a PR, or cite the repository publicly.

This is not an `ADOPTERS.md` substitute. A repository becomes an adopter only after it runs SkillOps
in its own CI or release evidence and gives permission to be listed.

## Adoption Goal

A good external adoption proves three things:

1. The repository can produce machine-readable SkillOps evidence without maintainer help.
2. Reviewers can understand why a check passed or failed from CI artifacts.
3. The team can decide whether to stay advisory, move to warning gate, or stop the rollout.

Do not start with hosted dashboards, custom SaaS state, or agent runtime integration. Start with the
open-source artifact contract.

## Intake Questions

Ask these before touching the repository:

| Question | Required answer |
| --- | --- |
| Who owns instruction governance for this repo? | A team or individual who can review skill metadata. |
| Which CI system will run SkillOps? | GitHub Actions is the reference path; other CI must preserve artifacts. |
| What is the first gate mode? | Advisory unless the repo already has mature skill metadata. |
| Are there external or copied skills? | If yes, import provenance and license metadata are required before blocking. |
| What artifacts can be retained? | At minimum: check JSON, SARIF, conformance report, registry, and evidence manifest. |
| Who reviews failures? | Platform, security, or repo owners must agree on rule ownership. |

## Minimum Repository Patch

The first external adoption should add only these files:

```text
config/skills.yaml
skills/
.github/workflows/skillops.yml
evidence/.gitkeep
```

Optional but recommended after the first run:

```text
AGENTS.md
skills.lock.json
```

Avoid committing generated evidence bundles unless the repository already has a release-evidence
policy. CI artifacts are enough for the first adoption.

## First Run Commands

Run locally before opening a pull request:

```bash
python3.12 -m pip install skills-orchestrator

skills-orchestrator init --template team-standard
skills-orchestrator check \
  --config config/skills.yaml \
  --policy-pack builtin/team-standard
skills-orchestrator build --lock
skills-orchestrator doctor --profile adopter --fail-under 90
skills-orchestrator conformance run --profile core
skills-orchestrator evidence export --out evidence
skills-orchestrator schema audit --stability stable
```

If the repository needs MCP serving, install it explicitly:

```bash
python3.12 -m pip install "skills-orchestrator[mcp]"
```

The MCP extra is not required for CI governance checks.

## Reference GitHub Action

Start with advisory mode:

```yaml
name: SkillOps

on:
  pull_request:
  push:
    branches: [main]

permissions:
  contents: read
  security-events: write
  pull-requests: write

jobs:
  skillops:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: BambooGap/skills-orchestrator@v4.8.45
        with:
          config: config/skills.yaml
          policy-pack: builtin/team-standard
          upload-sarif: true
          registry-diff: true
          reviewer-summary: true
          dashboard-snapshot: true
          comment-registry-diff: true
```

Adjust the `branches` value to the repository's real default branch before the first adoption run.
Many external repositories still use `master` or another protected branch name; leaving the starter
workflow pinned to `main` can make the SkillOps CI artifact disappear from the adoption path and keep
`doctor --profile adopter` below 100.

Move to warning gate only after reviewers understand the output:

```yaml
          fail-on: warning
```

## Evidence To Review

The first CI run should produce or make available:

| Artifact | Purpose |
| --- | --- |
| `check.json` | Stable machine-readable diagnostics and policy trace. |
| SARIF upload | Code scanning integration for policy findings. |
| `ci-explainability.json` | PR-level explanation for failures. |
| registry diff comment | Reviewer-facing skill changes. |
| `skills.lock.json` | Drift detection and reproducibility. |
| `conformance` report | Proof the repo satisfies the core SkillOps contract. |
| `evidence/evidence-manifest.json` | Release/audit evidence bundle entry point. |

If the team cannot find or interpret these artifacts, keep the adoption advisory.

## Promotion Gates

### Advisory To Warning Gate

Required:

- `doctor --profile adopter` is `100/100`.
- `conformance run --profile core` passes.
- `check --policy-pack builtin/team-standard --fail-on warning` has no findings.
- `skills.lock.json` is committed or reviewed as a required generated artifact.
- PR reviewers can explain the registry diff and SARIF findings.

### Warning Gate To Engineering Gate

Required:

- Every skill has `owner`, `source`, `version`, `lifecycle`, `approvers`, and `license`.
- Every external skill has import provenance with source URL, resolved ref, content hash, and
  fetched timestamp.
- Review-window metadata is present and current.
- Negative conformance fixtures or equivalent bad inputs fail with expected rule ids.
- Release owners accept the rollback path for bad SkillOps releases or broken generated artifacts.

Use:

```bash
skills-orchestrator check \
  --config config/skills.yaml \
  --policy-pack builtin/engineering-grade \
  --fail-on warning
```

## Stop Conditions

Stop or keep advisory when:

- The repository cannot retain CI artifacts.
- Reviewers cannot map failures to owners.
- Skill metadata is generated but no one owns it.
- External skills lack provenance or license information.
- The workflow requires `pull_request_target` for untrusted forks without a reviewed threat model.
- The adoption needs custom hosted state before the OSS artifact contract works.

## Adoption Handoff Record

For a real external adoption, keep a short record and validate it before treating the adoption as review
evidence:

```bash
skills-orchestrator schema validate \
  --kind external-adoption-record \
  --input adoption-record.json
```

The record should use this shape:

```json
{
  "schema_version": "skills-orchestrator.external-adoption-record.v1",
  "adoption": {
    "repository": "owner/repo",
    "adoption_owner": "team-or-person",
    "started_at": "YYYY-MM-DD",
    "skillops_version": "v4.8.45",
    "ci_system": "github-actions"
  },
  "authorization": {
    "tier": "private-technical-adoption",
    "requested_at": "YYYY-MM-DD",
    "decided_at": "YYYY-MM-DD",
    "approved_by": "repo-maintainer",
    "notes": "Private technical adoption only; no public listing or case study is approved."
  },
  "gate": {
    "mode": "advisory",
    "policy_pack": "builtin/team-standard",
    "fail_on": "none"
  },
  "artifacts": {
    "check_json": { "status": "present", "path": "artifacts/check.json" },
    "sarif": { "status": "present", "path": "artifacts/skills-orchestrator.sarif" },
    "registry_diff": { "status": "present", "path": "artifacts/registry-diff.md" },
    "evidence_manifest": {
      "status": "present",
      "path": "artifacts/evidence/evidence-manifest.json"
    },
    "conformance_report": { "status": "present", "path": "artifacts/conformance.json" }
  },
  "promotion": {
    "decision": "stay-advisory",
    "decided_at": "YYYY-MM-DD",
    "next_review": "YYYY-MM-DD"
  },
  "public_listing": {
    "status": "not-requested"
  }
}
```

Only create or update `ADOPTERS.md` after the repository owner explicitly allows public listing and
the external adoption record carries a public adopter/reference or public case-study authorization tier.
For a runnable reference example, see
[`examples/external-adoption-record`](../examples/external-adoption-record/README.md).

Use `authorization.tier` to record what the maintainer approved:

- `not-requested`: no adoption authorization has been requested yet.
- `pending`: authorization was requested and no decision has been recorded.
- `declined-no-follow-up`: the maintainer declined or closed the request; do not follow up or cite.
- `private-technical-adoption`: artifacts may be shared privately with the maintainer.
- `public-adoption-mention`: public evaluation mention is allowed, but not adopter/case language.
- `public-adopter-reference`: public adopter/reference listing is approved.
- `public-case-study`: a case study, quote, or artifact excerpt is approved.

`public_listing.status=approved` is valid only with `public-adopter-reference` or
`public-case-study`. Private, pending, declined, and public-mention-only adoptions must not be listed
as adopters.

## Evidence Pack And Case Study

After the first CI run, collect the artifacts with [Adoption Evidence Pack](adoption-evidence-pack.md).
That document defines the handoff directory, required artifacts, review agenda, and promotion
decisions for a real external repository adoption.

If the repository owner approves public listing, use
[Adoption Case Study Template](adoption-case-study-template.md) to write a public case. Do not publish a
case study, logo, quote, or `ADOPTERS.md` entry unless `public_listing.status` is `approved` and
`authorization.tier` is `public-adopter-reference` or `public-case-study`.
