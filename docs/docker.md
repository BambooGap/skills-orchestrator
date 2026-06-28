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
docker run --rm ghcr.io/bamboogap/skills-orchestrator:v4.8.20 --version
```

## Run Against A Repository

Mount the repository at `/workspace` and run commands from that directory:

```bash
docker run --rm \
  -v "$PWD:/workspace" \
  -w /workspace \
  ghcr.io/bamboogap/skills-orchestrator:v4.8.20 \
  check --config config/skills.yaml
```

Generate audit artifacts:

```bash
docker run --rm \
  -v "$PWD:/workspace" \
  -w /workspace \
  ghcr.io/bamboogap/skills-orchestrator:v4.8.20 \
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
Dockerfile. CI runs `scripts/check_docker_base_digest.py` so future Dockerfile changes cannot
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
keyless signing, and generates:

- `container-sbom.cdx.json`: a CycloneDX SBOM bound to the immutable OCI digest,
- `container-provenance.json`: a SkillOps provenance contract that records the image subject,
  source commit, workflow run, and SBOM hash.

Both the build provenance and SBOM are attested with GitHub Artifact Attestations using
`subject-name: ghcr.io/bamboogap/skills-orchestrator` and the resolved `sha256:` digest. The image
signature, provenance, and SBOM are separate release evidence surfaces: the signature proves the
workflow signed the digest, while attestations attach structured evidence to that digest. The SBOM
describes the SkillOps package dependency surface inside the image; it is not a full operating-system
layer scan.

See [Supply Chain Verification](supply-chain-verification.md) for the consuming-repository commands
that verify the GHCR image signature, provenance attestation, and CycloneDX SBOM attestation against
the release tag and workflow identity.

Future hardening should add a full operating-system layer SBOM and avoid claiming a formal SLSA
level until the release process is audited against that level.
