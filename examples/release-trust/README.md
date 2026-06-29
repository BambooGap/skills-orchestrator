# Release Trust And External Skill Provenance Example

This example demonstrates the v4.4 trust boundary for releases and externally sourced skills.

It covers:

- engineering-grade checks for externally sourced skills,
- MIT / Apache-2.0 license allowlist behavior,
- review-window metadata requirements,
- import provenance requirements,
- local verification of container release provenance and SBOM hash binding.

## Valid External Skill Gate

The valid fixture set includes a synthetic reviewed skill and a real Hermes
Tweet source-linked skill, so downstream teams can test license and provenance
metadata against both placeholder and public package examples.

```bash
skills-orchestrator check \
  --config config/valid-skills.yaml \
  --policy-pack builtin/engineering-grade \
  --fail-on warning
```

Expected result: `0 errors, 0 warnings, 0 infos`.

## Invalid External Skill Gate

```bash
skills-orchestrator check \
  --config config/invalid-external-skills.yaml \
  --policy-pack builtin/engineering-grade \
  --format json \
  > evidence/invalid-check.json
```

Expected rules:

- `SO014`: missing review-window metadata,
- `SO018`: missing license metadata,
- `SO020`: missing external import provenance.

## Container Release Verification

```bash
mkdir -p evidence

skills-orchestrator supply-chain container-release \
  --image ghcr.io/bamboogap/skills-orchestrator \
  --tag v4.8.35 \
  --digest sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa \
  --repository BambooGap/skills-orchestrator \
  --commit local-fixture \
  --workflow-run-url https://github.com/BambooGap/skills-orchestrator/actions/runs/0 \
  --sbom-output evidence/container-sbom.cdx.json \
  --provenance-output evidence/container-provenance.json \
  --no-dependencies \
  --force

skills-orchestrator supply-chain verify-container-release \
  --provenance evidence/container-provenance.json \
  --sbom evidence/container-sbom.cdx.json \
  --image ghcr.io/bamboogap/skills-orchestrator \
  --tag v4.8.35 \
  --digest sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
```

This verifies local release evidence. It does not replace GitHub Artifact Attestation verification
for a real GHCR image digest.
