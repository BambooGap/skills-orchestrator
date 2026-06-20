# Docker Usage

The Docker image is a portable CLI runtime for CI systems that should not install Python packages
directly on the host.

## Build Locally

```bash
docker build -t skills-orchestrator:local .
docker run --rm skills-orchestrator:local --version
```

## Run Against A Repository

Mount the repository at `/workspace` and run commands from that directory:

```bash
docker run --rm \
  -v "$PWD:/workspace" \
  -w /workspace \
  skills-orchestrator:local \
  check --config config/skills.yaml
```

Generate audit artifacts:

```bash
docker run --rm \
  -v "$PWD:/workspace" \
  -w /workspace \
  skills-orchestrator:local \
  manifest --config config/skills.yaml --format cyclonedx \
  --output instruction-manifest.cdx.json
```

## Dependency Policy

The image installs the project with `constraints.txt`. This constrains the dependency set for the
build, but it is not a hash-locked supply-chain install yet. The image does not run an unpinned pip
upgrade step and runs the CLI as a non-root user.

A future release should move Docker and CI to a hash-locked constraints workflow, publish to GHCR,
generate an image SBOM, and sign images with provenance.
