# SLSA Readiness

Skills Orchestrator publishes release evidence that can be mapped to SLSA build-track concepts, but
it does not claim a formal SLSA level. Treat this page and the generated report as an adoption aid
for platform teams, not as a certification statement.

The current mapping follows the SLSA v1.2 build requirements:

- Producer responsibilities: choose an appropriate build platform, follow a consistent build
  process, and distribute provenance.
- Build-platform responsibilities: generate provenance, make it authentic, and provide isolation
  strength appropriate to the desired level.

Reference: <https://slsa.dev/spec/v1.2/build-requirements>

## Generate The Report

```bash
skills-orchestrator supply-chain slsa-readiness \
  --version v4.8.30 \
  --repository BambooGap/skills-orchestrator \
  --image ghcr.io/bamboogap/skills-orchestrator \
  --digest sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa \
  --output slsa-readiness.json \
  --force
```

Validate it:

```bash
skills-orchestrator schema validate --kind slsa-readiness --input slsa-readiness.json
```

The report is intentionally conservative:

- `build_l1`: `evidence-ready`
- `build_l2`: `evidence-ready`
- `build_l3`: `not-claimed`
- `source_track`: `not-claimed`
- `formal_claim`: `false`

## What The Report Means

The report records that Skills Orchestrator release evidence currently includes:

- PyPI wheel and sdist attestations,
- GHCR build provenance attestation,
- GHCR package SBOM attestation,
- GHCR Syft OS/image SBOM attestation,
- GHCR Cosign keyless image signature,
- full post-release smoke with retained JSON artifact,
- consumer-side hash-locked PyPI install smoke.

This is enough to support production CI governance decisions such as "can this exact release pin be
promoted into a consuming repository?" It is not enough to state "this project is SLSA certified" or
"this build is SLSA Build L3."

## What Is Not Claimed

The report explicitly does not claim:

- formal SLSA certification or level declaration,
- SLSA Build L3 hardened builder assessment,
- SLSA Source track conformance,
- runtime admission control,
- tenant, budget, secret, or worker isolation.

## Production Release Cadence

High-frequency patch releases are useful while the release evidence surface is being hardened, but
production consumers should not auto-promote every tag.

Recommended consuming policy:

1. Pin exact PyPI versions and GHCR digests.
2. Promote only releases whose full post-release smoke has `failed: 0`.
3. Require `slsa-readiness.json` and `post-release-smoke.json` in the release evidence bundle.
4. Hold new production pins for one business day unless the release fixes a blocking CI or security
   issue.
5. Keep the previous known-good release pin and rollback command in the consuming repository.

This keeps the project open and fast-moving while giving platform teams a stable promotion path.
