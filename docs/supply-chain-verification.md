# Supply Chain Verification

Use this guide when a consuming repository needs to verify a released Skills Orchestrator package or
container before using it in production CI.

This guide verifies release artifacts. It does not claim that Skills Orchestrator is an agent
runtime control plane, tenant isolation layer, budget enforcer, secret broker, worker sandbox,
independent image-signing system, or formal SLSA level certification.

## Required Tools

- GitHub CLI with attestation support: `gh attestation verify --help`
- Docker Buildx for image digest inspection: `docker buildx imagetools inspect`
- Python 3.12 or newer

Authenticate to GitHub/GHCR before verifying OCI attestations:

```bash
gh auth status
docker login ghcr.io
```

## Verify Release Identity

Set the release version and repository:

```bash
VERSION=v4.8.17
PYPI_VERSION="${VERSION#v}"
REPO=BambooGap/skills-orchestrator
IMAGE=ghcr.io/bamboogap/skills-orchestrator
```

Resolve the immutable GitHub Action commit:

```bash
git ls-remote https://github.com/BambooGap/skills-orchestrator.git "refs/tags/${VERSION}"
```

Resolve the immutable GHCR image digest:

```bash
docker buildx imagetools inspect "${IMAGE}:${VERSION}"
```

Production workflows should execute the resolved commit SHA and image digest, not only the tag.

## Verify PyPI Artifacts

Download the release artifacts from PyPI:

```bash
rm -rf /tmp/skillops-pypi-verify
mkdir -p /tmp/skillops-pypi-verify

python3.12 -m pip download \
  --no-deps \
  --dest /tmp/skillops-pypi-verify \
  "skills-orchestrator==${PYPI_VERSION}"
```

Verify the wheel provenance attestation:

```bash
gh attestation verify \
  "/tmp/skillops-pypi-verify/skills_orchestrator-${PYPI_VERSION}-py3-none-any.whl" \
  --repo "${REPO}" \
  --signer-workflow "${REPO}/.github/workflows/publish.yml" \
  --source-ref "refs/tags/${VERSION}"
```

Verify the source distribution provenance attestation:

```bash
gh attestation verify \
  "/tmp/skillops-pypi-verify/skills_orchestrator-${PYPI_VERSION}.tar.gz" \
  --repo "${REPO}" \
  --signer-workflow "${REPO}/.github/workflows/publish.yml" \
  --source-ref "refs/tags/${VERSION}"
```

These checks prove that the downloaded files have GitHub Artifact Attestations from the expected
release workflow and tag. They do not replace dependency hash locking in the consuming repository.

## Verify GHCR Provenance And SBOM

Resolve the release image digest and export it:

```bash
IMAGE_DIGEST="$(
  docker buildx imagetools inspect "${IMAGE}:${VERSION}" \
    | awk '/^Digest:/ {print $2; exit}'
)"
test -n "${IMAGE_DIGEST}"
```

Verify the image build provenance attestation from the OCI registry:

```bash
gh attestation verify \
  "oci://${IMAGE}@${IMAGE_DIGEST}" \
  --repo "${REPO}" \
  --signer-workflow "${REPO}/.github/workflows/ghcr.yml" \
  --source-ref "refs/tags/${VERSION}" \
  --bundle-from-oci
```

Verify the CycloneDX SBOM attestation from the OCI registry:

```bash
gh attestation verify \
  "oci://${IMAGE}@${IMAGE_DIGEST}" \
  --repo "${REPO}" \
  --signer-workflow "${REPO}/.github/workflows/ghcr.yml" \
  --source-ref "refs/tags/${VERSION}" \
  --bundle-from-oci \
  --predicate-type https://cyclonedx.org/bom
```

The GHCR SBOM describes the SkillOps package dependency surface in the image. It is not a full
operating-system layer SBOM.

## Optional Offline Attestation Archive

Download attestation bundles for evidence retention:

```bash
rm -rf /tmp/skillops-attestations
mkdir -p /tmp/skillops-attestations
cd /tmp/skillops-attestations

gh attestation download \
  "oci://${IMAGE}@${IMAGE_DIGEST}" \
  --repo "${REPO}"
```

Store the downloaded JSONL bundle with the release evidence bundle and `post-release-smoke.json`.

## Consumer-Side Hash-Locked Install

`skills-orchestrator==4.8.17` is an exact version pin, not a hash-locked install. Repositories that
require hash locking should create and own a requirements lock that includes every transitive
dependency hash.

One common pattern is:

```bash
python3.12 -m pip install pip-tools

cat > requirements.in <<'EOF'
skills-orchestrator==4.8.17
EOF

pip-compile \
  --generate-hashes \
  --output-file requirements.lock \
  requirements.in

python3.12 -m pip install --require-hashes -r requirements.lock
```

This lock file belongs to the consuming repository because transitive dependency policy, allowed
indexes, mirrors, and refresh cadence are organization-specific.

## Production Acceptance Checklist

For a production CI rollout, keep evidence that:

- the Action reference is pinned to the release commit SHA;
- the Docker reference is pinned to the image digest;
- PyPI wheel and sdist attestations verify against `publish.yml` and the release tag;
- GHCR provenance and CycloneDX SBOM attestations verify against `ghcr.yml` and the release tag;
- `post-release-smoke.json` passes schema validation with `failed: 0`;
- the consuming repo has its own dependency hash-locking policy if direct PyPI installation is used;
- runtime enforcement remains outside SkillOps and is owned by the agent platform/provider.

## Current Boundaries

Implemented:

- PyPI Trusted Publishing with artifact attestations for wheel and sdist.
- GHCR multi-arch image publishing.
- GHCR digest-bound SLSA provenance attestation.
- GHCR digest-bound CycloneDX SBOM attestation.
- Post-release smoke for GitHub Release, PyPI, GHCR, default install, and starter-kit path.

Not claimed:

- Independent image signing policy.
- Formal SLSA level.
- Full operating-system layer SBOM.
- Runtime admission control.
- Runtime tenant, budget, secret, or worker isolation.
