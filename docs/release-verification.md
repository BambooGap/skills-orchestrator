# Release Verification

Use this checklist before publishing a release or after cutting a tag.

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
- Publish workflow used Trusted Publishing.
- GitHub Release points to the intended tag and commit.
- PyPI shows the intended version as latest.
- Wheel and sdist are present.
- PyPI provenance / attestations are visible for both artifacts.
- CodeQL workflow completed or is intentionally skipped for the tag.
- GHCR workflow published the release image when container publishing is enabled.
- GHCR image provenance and SBOM attestations are attached to the resolved image digest.

## Current Gaps

The release workflow attests Python distribution artifacts and the GHCR workflow publishes release
images with digest-bound provenance and SBOM attestations. Image signing, full operating-system
layer SBOMs, SLSA level claims, and hash-locked Python installs remain future hardening items.
