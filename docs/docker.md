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
docker run --rm ghcr.io/bamboogap/skills-orchestrator:v3.0.6 --version
```

## Run Against A Repository

Mount the repository at `/workspace` and run commands from that directory:

```bash
docker run --rm \
  -v "$PWD:/workspace" \
  -w /workspace \
  ghcr.io/bamboogap/skills-orchestrator:v3.0.6 \
  check --config config/skills.yaml
```

Generate audit artifacts:

```bash
docker run --rm \
  -v "$PWD:/workspace" \
  -w /workspace \
  ghcr.io/bamboogap/skills-orchestrator:v3.0.6 \
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
not push images.

Future hardening should add image SBOM/provenance tied to the pushed digest and move Docker/CI to a
hash-locked constraints workflow.
