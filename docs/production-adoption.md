# Production Adoption

Use this guide when a repository is ready to run Skills Orchestrator in production CI. The scope is
intentionally narrow: SkillOps is a CI governance gate for AI instruction artifacts. It is not an
agent runtime control plane, tenant-isolation layer, budget enforcer, secret broker, or worker
sandbox.

## Production Scope

Skills Orchestrator can block or warn on:

- `skills.yaml` structure and schema validity,
- skill metadata, ownership, lifecycle, review windows, license, and import provenance,
- registry drift and PR review summaries,
- SARIF / Code Scanning diagnostics,
- evidence bundle generation and schema validation,
- conformance reports,
- release trust metadata and container release evidence.

Skills Orchestrator cannot prove:

- worker agents actually ran,
- runtime permissions were enforced,
- tenant isolation was enforced,
- budgets or rate limits were enforced,
- secrets were isolated from prompts or worker processes,
- `agent-handoff` or `agent-runtime-image` artifacts became runtime policy.

Treat `agent-handoff` and `agent-runtime-image` as review artifacts. They make boundaries visible
before execution; the runtime, platform, or provider must enforce those boundaries.

## Minimum Production Configuration

For production CI, pin every moving part:

| Surface | Minimum production rule |
| --- | --- |
| GitHub Action | Pin `actions/checkout` and `BambooGap/skills-orchestrator` to full commit SHAs. |
| PyPI CLI | Pin an exact version such as `skills-orchestrator==4.8.17`. |
| Docker image | Pin the GHCR digest, not only `:v4.8.17`. |
| Policy pack | Start with `builtin/team-standard`; promote to `builtin/engineering-grade` when owners accept external import and license requirements. |
| Evidence | Retain `check.json`, SARIF, `ci-explainability.json`, registry outputs, `evidence-manifest.json`, and post-release smoke output. |
| Rollback | Keep a documented rollback owner and downgrade path before enabling blocking gates. |

Use [Supply Chain Verification](supply-chain-verification.md) before promoting a new SkillOps
release pin in production CI.

## Resolve Release Pins

Resolve the action commit from the release tag:

```bash
git ls-remote https://github.com/BambooGap/skills-orchestrator.git refs/tags/v4.8.17
```

Resolve the image digest:

```bash
docker buildx imagetools inspect ghcr.io/bamboogap/skills-orchestrator:v4.8.17
```

Use the returned SHA and digest in production workflows. Keep the tag in comments or documentation
for human readability, but make the executable reference immutable.

## Production GitHub Action

This is the recommended production shape. Replace the two placeholder SHAs with resolved release
values.

```yaml
name: SkillOps production gate

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
      # v4-compatible checkout pinned to a full commit SHA.
      - uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683
        with:
          fetch-depth: 0

      # Resolve with:
      # git ls-remote https://github.com/BambooGap/skills-orchestrator.git refs/tags/v4.8.17
      - id: skillops
        uses: BambooGap/skills-orchestrator@<skills-orchestrator-release-commit-sha>
        with:
          config: config/skills.yaml
          check-lock: skills.lock.json
          policy-pack: builtin/team-standard
          fail-on: warning
          upload-sarif: true
          registry-diff: true
          reviewer-summary: true
          dashboard-snapshot: true
          comment-registry-diff: true

      - name: Upload SkillOps evidence
        uses: actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a
        with:
          name: skillops-evidence
          path: |
            ${{ steps.skillops.outputs.check-json-file }}
            ${{ steps.skillops.outputs.policy-trace-file }}
            ${{ steps.skillops.outputs.ci-explainability-file }}
            ${{ steps.skillops.outputs.registry-diff-file }}
            ${{ steps.skillops.outputs.registry-diff-json-file }}
            ${{ steps.skillops.outputs.registry-graph-file }}
            ${{ steps.skillops.outputs.evidence-manifest-file }}
            ${{ steps.skillops.outputs.reviewer-summary-file }}
            ${{ steps.skillops.outputs.dashboard-snapshot-file }}
```

## Advisory To Blocking Promotion

Use staged rollout instead of enabling the strictest gate on day one.

| Stage | Gate | Exit criteria |
| --- | --- | --- |
| 1. Advisory | `check`, `schema audit`, `conformance run --profile core`, `evidence export` | Two weeks of runs with reviewers understanding SARIF and registry diff output. |
| 2. Team blocking | `builtin/team-standard --fail-on warning` | Skill owners, source, version, lifecycle, and lock drift are accepted by repo owners. |
| 3. Engineering-grade blocking | `builtin/engineering-grade --fail-on warning` | External imports have license/provenance metadata and review windows. |
| 4. Release gate | Post-release smoke, release trust, evidence retention, rollback playbook | Release owners can prove what was published and how to roll back. |

If a gate creates noisy findings, lower the gate for one release and keep the evidence. Do not
delete or rewrite release artifacts to hide a bad run.

## Evidence Retention

Retain these artifacts for production repositories:

- `skills-orchestrator.sarif`,
- `check.json`,
- `ci-explainability.json`,
- `policy-trace.json`,
- `skill-registry.json`,
- `registry-diff.json` and `registry-diff.md`,
- `registry-graph.json`,
- `evidence/evidence-manifest.json`,
- `skillops-review-summary.md`,
- `dashboard-snapshot.json`,
- `post-release-smoke.json` for released versions.

Recommended retention:

| Artifact | Retention |
| --- | --- |
| PR artifacts | 30-90 days, matching repository CI retention. |
| Release evidence | At least one year or the product's release support window. |
| Security-relevant evidence | Follow the organization's security evidence retention policy. |

## Docker In Production CI

Use the image digest for execution:

```bash
docker run --rm \
  -v "$PWD:/workspace" \
  -w /workspace \
  ghcr.io/bamboogap/skills-orchestrator@sha256:<resolved-image-index-digest> \
  check --config config/skills.yaml --policy-pack builtin/team-standard --fail-on warning
```

The release workflow publishes GHCR SBOM/provenance attestations. Use
[Supply Chain Verification](supply-chain-verification.md) to verify the released digest with GitHub
Artifact Attestations. `verify-container-release` validates local SkillOps container release
artifacts, but it is not a substitute for runtime admission control, image signing policy, or
artifact attestation verification in your deployment platform.

## PyPI In Production CI

For CI hosts that install the CLI directly, pin the version:

```bash
python3.12 -m pip install "skills-orchestrator==4.8.17"
skills-orchestrator schema audit
skills-orchestrator check --config config/skills.yaml --policy-pack builtin/team-standard --fail-on warning
```

Use the optional MCP extra only when the CI job intentionally runs MCP smoke checks:

```bash
python3.12 -m pip install "skills-orchestrator[mcp]==4.8.17"
```

Exact version pins are not hash-locked installs. If the organization requires hash locking, generate
and own a consumer-side lock file as described in
[Supply Chain Verification](supply-chain-verification.md#consumer-side-hash-locked-install).

## Runtime Boundary Checklist

Before using handoff or runtime image artifacts with real agents, confirm:

- the runtime enforces tenant/project boundaries independently of SkillOps;
- privileged worker actions require platform approval, not only prompt instructions;
- secrets are injected by the runtime or provider, not by skill files;
- budget and rate limits are enforced by the provider or platform layer;
- worker logs do not leak tenant data, keys, or cross-tenant memory;
- `agent-handoff` and `agent-runtime-image` artifacts are validated in CI before runtime launch.

## Rollback

When a SkillOps release or policy pack blocks production unexpectedly:

1. Preserve the failing SARIF, check JSON, registry diff, and evidence manifest.
2. Revert the repo's SkillOps Action SHA or PyPI version pin to the last known-good release.
3. If a policy pack is too strict, lower the gate from blocking to advisory for one release.
4. File a fix with the failing artifact attached.
5. Re-promote to blocking after the fixed release passes post-release smoke.

Use [Release Rollback](release-rollback.md) for project release incidents and
[Adoption Playbook](adoption-playbook.md) for repository-level promotion.
