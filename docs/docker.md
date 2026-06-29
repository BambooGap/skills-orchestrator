# Docker Usage

The Docker image is a portable CLI runtime for CI systems that should not install Python packages
directly on the host.

## Build Locally

```bash
docker build -t skills-orchestrator:local .
docker run --rm skills-orchestrator:local --version
```

Use the published release image when a CI host should not build the project first:

```bash
docker run --rm ghcr.io/bamboogap/skills-orchestrator:v4.8.42 --version
```

## Run Against A Repository

Mount the repository at `/workspace` and run commands from that directory:

```bash
docker run --rm \
  -v "$PWD:/workspace" \
  -w /workspace \
  ghcr.io/bamboogap/skills-orchestrator:v4.8.42 \
  check --config config/skills.yaml
```

Generate audit artifacts:

```bash
docker run --rm \
  -v "$PWD:/workspace" \
  -w /workspace \
  ghcr.io/bamboogap/skills-orchestrator:v4.8.42 \
  manifest --config config/skills.yaml --format cyclonedx \
  --output instruction-manifest.cdx.json
```

## Dependency Policy

The image installs the project with `constraints.txt`. This constrains the dependency set for the
build, while post-release smoke verifies that the published PyPI package can also install from a
consumer-side `--require-hashes` wheelhouse. CI runs `scripts/check_pip_constraints.py` so automation
cannot accidentally add an unconstrained `pip install` path. The image does not run an unpinned pip
upgrade step and runs the CLI as a non-root user.

The Docker base image is pinned to the `python:3.12.13-slim-trixie` manifest-list digest in the
Dockerfile. CI runs `scripts/check_docker_base_digest.py` so Dockerfile changes cannot
silently return to a floating base tag.

## GHCR Publishing

`.github/workflows/ghcr.yml` publishes release and manual images to:

```text
ghcr.io/bamboogap/skills-orchestrator
```

Release builds are tagged with the release ref and a short commit SHA tag. Pull request workflows do
not push images. v4.6.5 and newer release images are published as multi-arch manifests for
`linux/amd64` and `linux/arm64`, so Apple Silicon and ARM CI hosts can run the released image
without a platform mismatch warning.

The release workflow resolves the pushed image digest, signs that digest with Sigstore Cosign
keyless signing, generates a Syft OS/image SBOM, and generates:

- `container-sbom.cdx.json`: a CycloneDX SBOM bound to the immutable OCI digest,
- `container-os-sbom.cdx.json`: a Syft-generated CycloneDX SBOM for the image filesystem/package
  surface,
- `container-provenance.json`: a SkillOps provenance contract that records the image subject,
  source commit, workflow run, and SBOM hash.

The build provenance, package SBOM, and OS/image SBOM are attested with GitHub Artifact Attestations
using `subject-name: ghcr.io/bamboogap/skills-orchestrator` and the resolved `sha256:` digest. The
image signature, provenance, package SBOM, and OS/image SBOM are separate release evidence surfaces:
the signature proves the workflow signed the digest, while attestations attach structured evidence to
that digest. The package SBOM describes the SkillOps Python dependency surface; the OS/image SBOM
describes what Syft can observe in the container filesystem and package manager layers.

See [Supply Chain Verification](supply-chain-verification.md) for the consuming-repository commands
that verify the GHCR image signature, provenance attestation, package SBOM attestation, and OS/image
SBOM attestation against the release tag and workflow identity.

## Restricted Network Or GHCR Fallback

Some enterprise or regional networks cannot pull from GHCR reliably. Treat that as a distribution
constraint, not as a reason to run an unverified floating image tag.

Preferred production pattern:

1. From a connected environment, resolve the release digest:

   ```bash
   VERSION=v4.8.42
   IMAGE=ghcr.io/bamboogap/skills-orchestrator
   docker buildx imagetools inspect "${IMAGE}:${VERSION}"
   ```

2. Verify the digest, Cosign signature, provenance attestation, package SBOM attestation, and
   OS/image SBOM attestation with [Supply Chain Verification](supply-chain-verification.md).

3. Promote the verified digest into an internal registry or image cache:

   ```bash
   docker pull "${IMAGE}@sha256:<verified-digest>"
   docker tag "${IMAGE}@sha256:<verified-digest>" internal.example.com/skillops/skills-orchestrator:v4.8.42
   docker push internal.example.com/skillops/skills-orchestrator:v4.8.42
   ```

4. In production CI, pin the internal image by digest:

   ```bash
   docker run --rm internal.example.com/skillops/skills-orchestrator@sha256:<internal-digest> --version
   ```

If OCI distribution is blocked entirely, use the PyPI wheelhouse path in [Install](install.md) and
retain the hash-locked requirements file plus PyPI attestation verification output with the release
evidence bundle.

Future hardening should add an explicit OS SBOM vulnerability-scanning policy and avoid claiming a
formal SLSA level until the release process is audited against that level.
