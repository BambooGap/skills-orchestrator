# External Pilot Intake

Use this checklist when a repository outside this project wants to trial Skills Orchestrator. It is
written for platform teams, security reviewers, and maintainers who need a clear go / no-go decision
before turning SkillOps into a blocking gate. If the repository owner has not approved a pilot yet,
start with [Authorized Pilot Outreach](pilot-outreach.md). If the owner closes the request or says
they are not interested, stop there; do not follow up, open a PR, or cite the repository publicly.

This is not an `ADOPTERS.md` substitute. A repository becomes an adopter only after it runs SkillOps
in its own CI or release evidence and gives permission to be listed.

## Pilot Goal

A good external pilot proves three things:

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

The first external pilot should add only these files:

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
policy. CI artifacts are enough for the first pilot.

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
      - uses: BambooGap/skills-orchestrator@v4.8.36
        with:
          config: config/skills.yaml
          policy-pack: builtin/team-standard
          upload-sarif: true
          registry-diff: true
          reviewer-summary: true
          dashboard-snapshot: true
          comment-registry-diff: true
```

Adjust the `branches` value to the repository's real default branch before the first pilot run.
Many external repositories still use `master` or another protected branch name; leaving the starter
workflow pinned to `main` can make the SkillOps CI artifact disappear from the pilot path and keep
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

If the team cannot find or interpret these artifacts, keep the pilot advisory.

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
- The pilot needs custom hosted state before the OSS artifact contract works.

## Pilot Handoff Record

For a real external pilot, keep a short record and validate it before treating the pilot as review
evidence:

```bash
skills-orchestrator schema validate \
  --kind external-pilot-record \
  --input pilot-record.json
```

The record should use this shape:

```json
{
  "schema_version": "skills-orchestrator.external-pilot-record.v1",
  "pilot": {
    "repository": "owner/repo",
    "pilot_owner": "team-or-person",
    "started_at": "YYYY-MM-DD",
    "skillops_version": "v4.8.36",
    "ci_system": "github-actions"
  },
  "authorization": {
    "tier": "private-technical-pilot",
    "requested_at": "YYYY-MM-DD",
    "decided_at": "YYYY-MM-DD",
    "approved_by": "repo-maintainer",
    "notes": "Private technical pilot only; no public listing or case study is approved."
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
the external pilot record carries a public adopter/reference or public case-study authorization tier.
For a runnable synthetic fixture, see
[`examples/external-pilot-record`](../examples/external-pilot-record/README.md).

Use `authorization.tier` to record what the maintainer approved:

- `not-requested`: no pilot authorization has been requested yet.
- `pending`: authorization was requested and no decision has been recorded.
- `declined-no-follow-up`: the maintainer declined or closed the request; do not follow up or cite.
- `private-technical-pilot`: artifacts may be shared privately with the maintainer.
- `public-pilot-mention`: public evaluation mention is allowed, but not adopter/case language.
- `public-adopter-reference`: public adopter/reference listing is approved.
- `public-case-study`: a case study, quote, or artifact excerpt is approved.

`public_listing.status=approved` is valid only with `public-adopter-reference` or
`public-case-study`. Private, pending, declined, and public-mention-only pilots must not be listed
as adopters.

## Evidence Pack And Case Study

After the first CI run, collect the artifacts with [Pilot Evidence Pack](pilot-evidence-pack.md).
That document defines the handoff directory, required artifacts, review agenda, and promotion
decisions for a real external repository pilot.

If the repository owner approves public listing, use
[Pilot Case Study Template](pilot-case-study-template.md) to write a public case. Do not publish a
case study, logo, quote, or `ADOPTERS.md` entry unless `public_listing.status` is `approved` and
`authorization.tier` is `public-adopter-reference` or `public-case-study`.
