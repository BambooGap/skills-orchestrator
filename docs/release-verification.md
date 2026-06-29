# Release Verification

Use this checklist before publishing a release or after cutting a tag.

If a release is already published and turns out to be wrong, use
[Release Rollback](release-rollback.md) before deleting tags, assets, or container images.

## Local Checks

```bash
python -m ruff format --check skills_orchestrator/ tests/ scripts/check_action_pins.py
python -m ruff check skills_orchestrator/ tests/ scripts/check_action_pins.py
python -m pytest
python scripts/check_action_pins.py
skills-orchestrator supply-chain sbom --output package-sbom.cdx.json
python -m json.tool package-sbom.cdx.json >/dev/null
skills-orchestrator supply-chain container-release \
  --image ghcr.io/bamboogap/skills-orchestrator \
  --tag local \
  --digest sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa \
  --sbom-output container-sbom.cdx.json \
  --provenance-output container-provenance.json \
  --no-dependencies
skills-orchestrator schema validate --kind container-provenance --input container-provenance.json
skills-orchestrator supply-chain verify-container-release \
  --provenance container-provenance.json \
  --sbom container-sbom.cdx.json \
  --image ghcr.io/bamboogap/skills-orchestrator \
  --tag local \
  --digest sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa \
  --format json > container-release-verification.json
skills-orchestrator schema validate \
  --kind container-release-verification \
  --input container-release-verification.json
skills-orchestrator supply-chain slsa-readiness \
  --version local \
  --repository BambooGap/skills-orchestrator \
  --image ghcr.io/bamboogap/skills-orchestrator \
  --digest sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa \
  --output slsa-readiness.json \
  --force
skills-orchestrator schema validate --kind slsa-readiness --input slsa-readiness.json
python -m build
python -m twine check dist/*
```

## SkillOps Smoke

```bash
skills-orchestrator check --config config/skills.yaml --format sarif \
  > skills-orchestrator.sarif
skills-orchestrator check --config config/skills.yaml --format json \
  > skills-orchestrator-check.json
skills-orchestrator explainability build \
  --check-json skills-orchestrator-check.json \
  --config config/skills.yaml \
  --output ci-explainability.json \
  --force
skills-orchestrator manifest --config config/skills.yaml --format json \
  --include-diagnostics --output instruction-manifest.json
skills-orchestrator manifest --config config/skills.yaml --format cyclonedx \
  --output instruction-manifest.cdx.json
skills-orchestrator policy export --config config/skills.yaml --format opa-input \
  --output policy-input.json
skills-orchestrator policy export --config config/skills.yaml --format rego-test \
  --output skills_orchestrator_policy_test.rego
skills-orchestrator registry build --config-glob config/skills.yaml --output registry-before.json
skills-orchestrator registry graph --config-glob config/skills.yaml --output registry-graph.json
cp registry-before.json registry-after.json
skills-orchestrator registry diff registry-before.json registry-after.json \
  --format markdown \
  --output registry-diff.md \
  --force
skills-orchestrator adapters inspect --format json > adapter-inspect.json
skills-orchestrator registry comment-body registry-diff.md --output registry-diff-comment.md
skills-orchestrator schema validate --kind check --input skills-orchestrator-check.json
skills-orchestrator schema validate --kind ci-explainability --input ci-explainability.json
skills-orchestrator schema validate --kind registry-graph --input registry-graph.json
skills-orchestrator schema validate --kind adapter-inspect --input adapter-inspect.json
skills-orchestrator schema validate --kind supply-chain-sbom --input package-sbom.cdx.json
skills-orchestrator schema validate --kind container-provenance --input container-provenance.json
skills-orchestrator schema validate \
  --kind container-release-verification \
  --input container-release-verification.json
skills-orchestrator supply-chain slsa-readiness \
  --version local \
  --repository BambooGap/skills-orchestrator \
  --image ghcr.io/bamboogap/skills-orchestrator \
  --digest sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa \
  --output slsa-readiness.json \
  --force
skills-orchestrator schema validate --kind slsa-readiness --input slsa-readiness.json
skills-orchestrator evidence export --config config/skills.yaml --out evidence
skills-orchestrator schema validate --kind evidence --input evidence/evidence-manifest.json
skills-orchestrator schema validate \
  --kind hosted-registry-ingest \
  --input examples/commercial-handoff/registry-ingest.json
```

## Docker Smoke

```bash
docker build -t skills-orchestrator:release .
docker run --rm skills-orchestrator:release --version
docker run --rm -v "$PWD:/workspace" -w /workspace \
  skills-orchestrator:release manifest --config config/skills.yaml --format json
```

If Docker is unavailable, record it as skipped with the daemon error.

## GitHub Evidence

Verify:

- CI is green for the release commit.
- The latest Post-release Smoke run for the released version is green. Older failed runs may remain
  in history, but the final run attached to the release decision must pass.
- Publish workflow used Trusted Publishing.
- GitHub Release points to the intended tag and commit.
- PyPI shows the intended version as latest.
- Wheel and sdist are present.
- PyPI provenance / attestations are visible for both artifacts.
- CodeQL workflow completed or is intentionally skipped for the tag.
- GHCR workflow published the release image when container publishing is enabled.
- GHCR image signature verifies against the `ghcr.yml` workflow identity.
- GHCR image provenance, package SBOM, and OS/image SBOM attestations are attached to the resolved
  image digest.
- PyPI wheel/sdist attestations and GHCR provenance/SBOM attestations verify with
  [Supply Chain Verification](supply-chain-verification.md) before a production pin is promoted.
- Local container provenance, SBOM subject, and SBOM hash binding pass
  `supply-chain verify-container-release`.
- A `slsa-readiness.json` report is generated and schema-valid; it must be archived as a
  non-certifying readiness map, not as a formal SLSA level claim.

## Post-Release Smoke

After PyPI and GHCR workflows finish, run the machine-readable public artifact smoke:

```bash
python scripts/post_release_smoke.py \
  --version v4.8.42 \
  --retries 8 \
  --retry-delay 15 \
  --format json > post-release-smoke.json
skills-orchestrator schema validate \
  --kind post-release-smoke \
  --input post-release-smoke.json
```

For a slower adopter-path check that installs the PyPI package in a clean virtual environment and
exercises the starter kit:

```bash
python scripts/post_release_smoke.py \
  --version v4.8.42 \
  --retries 8 \
  --retry-delay 20 \
  --check-pypi-install \
  --check-pypi-hash-lock \
  --check-new-user-path \
  --python python3.12 \
  --format json > post-release-smoke-full.json
skills-orchestrator schema validate \
  --kind post-release-smoke \
  --input post-release-smoke-full.json
```

Treat this as the final release hygiene gate: if a previous post-release smoke
failed, rerun it after the fix and use the latest successful run as the release
record.

The default smoke checks:

- GitHub Release tag, draft, and prerelease state,
- PyPI latest version, wheel, and sdist presence,
- GHCR manifest digest,
- required `linux/amd64` and `linux/arm64` platforms,
- GHCR attestation manifests.

The same check is available from the GitHub Actions UI through the `Post-release Smoke` workflow.
Use the release tag as the `version` input, for example `v4.8.42`. The workflow runs `full_smoke`
by default so the retained report covers public artifact metadata, PyPI clean install, consumer-side
hash-locked install, GHCR Cosign signature verification, GHCR OS SBOM attestation verification, the
SLSA readiness report schema check, starter-kit adopter path, and the default-install MCP extra
hint. Disable `full_smoke` only when you intentionally want a faster metadata-only check. The
workflow uploads `post-release-smoke.json` as a retained run artifact so platform teams can review or
archive the release verification evidence after the job finishes.

## Verification Scope

The release workflow attests Python distribution artifacts and the GHCR workflow publishes release
images with keyless Cosign signatures plus digest-bound provenance, package SBOM, and OS/image SBOM
attestations.
[Supply Chain Verification](supply-chain-verification.md) documents consumer-side verification for
those signatures and attestations. [SLSA Readiness](slsa-readiness.md) documents the generated
readiness map that links this evidence to SLSA build-track concepts without claiming a formal SLSA
level.

`skills-orchestrator==4.8.42` is still only an exact version pin, but the full post-release smoke now
proves the release can be installed from a locally generated wheelhouse with `--require-hashes`.
`verify-container-release` validates local SkillOps release artifacts; it is not a replacement for
Cosign or GitHub Artifact Attestation verification against a real GHCR digest.

For consuming repositories, [Production Adoption](production-adoption.md) defines the current
minimum production posture: full Action SHA pinning, Docker digest execution, PyPI exact-version
installs, evidence retention, and a staged advisory-to-blocking rollout.

Rollback drills are documented in [Release Rollback](release-rollback.md). The default incident
response is to publish a fixed patch release and preserve evidence, not to rewrite published
history.
