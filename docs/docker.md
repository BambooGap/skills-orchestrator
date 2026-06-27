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
docker run --rm ghcr.io/bamboogap/skills-orchestrator:v4.7.2 --version
```

## Run Against A Repository

Mount the repository at `/workspace` and run commands from that directory:

```bash
docker run --rm \
  -v "$PWD:/workspace" \
  -w /workspace \
  ghcr.io/bamboogap/skills-orchestrator:v4.7.2 \
  check --config config/skills.yaml
```

Generate audit artifacts:

```bash
docker run --rm \
  -v "$PWD:/workspace" \
  -w /workspace \
  ghcr.io/bamboogap/skills-orchestrator:v4.7.2 \
  manifest --config config/skills.yaml --format cyclonedx \
  --output instruction-manifest.cdx.json
```

## Dependency Policy

The image installs the project with `constraints.txt`. This constrains the dependency set for the
build, but it is not a hash-locked supply-chain install yet. The image does not run an unpinned pip
upgrade step and runs the CLI as a non-root user.

## GHCR Publishing

`.github/workflows/ghcr.yml` publishes release and manual images to:

```text
ghcr.io/bamboogap/skills-orchestrator
```

Release builds are tagged with the release ref and a short commit SHA tag. Pull request workflows do
not push images. v4.6.5 and newer release images are published as multi-arch manifests for
`linux/amd64` and `linux/arm64`, so Apple Silicon and ARM CI hosts can run the released image
without a platform mismatch warning.

The release workflow resolves the pushed image digest, generates:

- `container-sbom.cdx.json`: a CycloneDX SBOM bound to the immutable OCI digest,
- `container-provenance.json`: a SkillOps provenance contract that records the image subject,
  source commit, workflow run, and SBOM hash.

Both the build provenance and SBOM are attested with GitHub Artifact Attestations using
`subject-name: ghcr.io/bamboogap/skills-orchestrator` and the resolved `sha256:` digest. The SBOM
describes the SkillOps package dependency surface inside the image; it is not a full operating-system
layer scan.

Future hardening should add image signing and move Docker/CI to a hash-locked constraints workflow.
