# Adoption Maturity Model

This model defines how a repository moves from a local SkillOps experiment to a production blocking
gate. It is intentionally artifact-driven: each level is proven by commands or CI outputs, not by
screenshots or project branding.

## Levels

| Level | Name | Recommended gate | Required evidence |
| --- | --- | --- | --- |
| 0 | Discovery | None | `schema audit` passes for the installed package. |
| 1 | Local pilot | Local advisory | `init --template team-standard`, `check`, `build --lock`, and `doctor --profile adopter` run locally. |
| 2 | CI advisory | CI fails on errors only | GitHub Action runs on pull requests and uploads JSON/SARIF artifacts. |
| 3 | Team warning gate | CI fails on warnings | `builtin/team-standard --fail-on warning`, lock drift, and registry diff are understood by reviewers. |
| 4 | Engineering gate | CI blocks high-risk instruction assets | `builtin/engineering-grade --fail-on warning`, release trust verification, agent handoff validation, and negative fixtures pass. |
| 5 | Multi-repo governance | Platform-owned rollout | Multiple repositories publish evidence manifests and a multi-repo artifact index validates. |
| 6 | External adoption | Independent usage | At least one repository not maintained by this project uses SkillOps in public CI or release evidence. |

## Promotion Checklist

### Level 0: Discovery

```bash
python3.12 -m pip install skills-orchestrator
skills-orchestrator --version
skills-orchestrator schema audit --format text
```

Exit criteria:

- The package installs from PyPI or runs from GHCR.
- `schema audit` passes.

### Level 1: Local Pilot

```bash
skills-orchestrator init --template team-standard
skills-orchestrator check --config config/skills.yaml
skills-orchestrator build --config config/skills.yaml --lock
skills-orchestrator doctor --profile adopter --config config/skills.yaml
skills-orchestrator conformance run --profile core --config config/skills.yaml
```

Exit criteria:

- `doctor --profile adopter` is `100/100` after `build --lock` creates `AGENTS.md` and
  `skills.lock.json`.
- The team can explain each generated starter skill.
- No blocking policy pack is required yet.

### Level 2: CI Advisory

Use the GitHub Action in advisory mode:

```yaml
- uses: BambooGap/skills-orchestrator@v4.8.25
  with:
    config: config/skills.yaml
    policy-pack: builtin/team-standard
    upload-sarif: true
    reviewer-summary: true
```

Exit criteria:

- Pull requests produce check JSON and SARIF.
- Reviewers can find `ci-explainability.json`.
- Failures are understood as advisory until owners accept blocking behavior.

### Level 3: Team Warning Gate

```bash
skills-orchestrator check \
  --config config/skills.yaml \
  --policy-pack builtin/team-standard \
  --fail-on warning
```

Exit criteria:

- Every shared skill has `owner`, `source`, `version`, and `lifecycle`.
- Required skills have `approvers`.
- `skills.lock.json` is committed and drift is reviewed.
- Registry diff comments are meaningful to reviewers.

### Level 4: Engineering Gate

```bash
skills-orchestrator check \
  --config config/skills.yaml \
  --policy-pack builtin/engineering-grade \
  --fail-on warning

python -m pytest tests/test_negative_conformance_examples.py

skills-orchestrator schema validate \
  --kind agent-handoff \
  --input examples/agent-handoff/release-review-handoff.json
```

Exit criteria:

- Every skill has review-window and license metadata.
- External skills have provenance metadata.
- Negative conformance fixtures fail with expected rule ids.
- Supervised-agent handoffs validate against `agent-handoff` when worker agents are in scope.
- Release trust verification is part of release or image publishing.

### Level 5: Multi-repo Governance

```bash
skills-orchestrator evidence index \
  --manifest "api=../api/evidence/evidence-manifest.json" \
  --manifest "web=../web/evidence/evidence-manifest.json" \
  --scope-name platform-pilot \
  --output evidence/multi-repo-artifacts.json

skills-orchestrator schema validate \
  --kind multi-repo-artifacts \
  --input evidence/multi-repo-artifacts.json
```

Exit criteria:

- Each repository publishes a Level 2 evidence bundle.
- Platform owners can compare bundle hashes, package versions, policy packs, and registry surfaces.
- Hosted dashboards or GitHub Apps consume artifacts instead of redefining CLI semantics.

### Level 6: External Adoption

Exit criteria:

- A repository outside this maintainer's control uses SkillOps in public CI or release artifacts.
- The maintainer has permission to cite it.
- The adopter has enough context to report bugs or compatibility issues.

Do not create an `ADOPTERS.md` entry before this level is real.

## Regression Rules

A repository should move down a level when:

- CI stops producing machine-readable artifacts,
- policy packs are disabled without an explicit migration note,
- evidence bundles are stale or missing,
- release trust verification no longer binds to the published artifact digest,
- reviewers cannot interpret blocking failures.

## Relationship To Commercial Value

Commercial value begins at Level 2 because the tool can already reduce PR review and audit work.
Serious enterprise value begins at Level 4 because instruction assets become enforceable release
inputs. Foundation readiness begins after Level 6 because external adoption and shared governance
are community facts, not local test results.
