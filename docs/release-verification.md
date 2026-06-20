# Release Verification

Use this checklist before publishing a release or after cutting a tag.

## Local Checks

```bash
python -m ruff format --check skills_orchestrator/ tests/ scripts/check_action_pins.py
python -m ruff check skills_orchestrator/ tests/ scripts/check_action_pins.py
python -m pytest
python scripts/check_action_pins.py
python -m build
python -m twine check dist/*
```

## SkillOps Smoke

```bash
skills-orchestrator check --config config/skills.yaml --format sarif \
  > skills-orchestrator.sarif
skills-orchestrator manifest --config config/skills.yaml --format json \
  --include-diagnostics --output instruction-manifest.json
skills-orchestrator manifest --config config/skills.yaml --format cyclonedx \
  --output instruction-manifest.cdx.json
skills-orchestrator policy export --config config/skills.yaml --format opa-input \
  --output policy-input.json
skills-orchestrator policy export --config config/skills.yaml --format rego-test \
  --output skills_orchestrator_policy_test.rego
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
- Publish workflow used Trusted Publishing.
- GitHub Release points to the intended tag and commit.
- PyPI shows the intended version as latest.
- Wheel and sdist are present.
- PyPI provenance / attestations are visible for both artifacts.

## Current Gaps

The release workflow attests Python distribution artifacts. Docker image publishing, image SBOM,
image signing, and SLSA image provenance are future hardening items.
