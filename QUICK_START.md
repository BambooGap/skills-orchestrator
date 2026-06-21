# Skills Orchestrator Quick Start

This is the shortest production path for a team repository.

## 1. Install

```bash
python3.12 -m pip install skills-orchestrator
skills-orchestrator --version
```

Other install paths are in [docs/install.md](docs/install.md).

## 2. Bootstrap A Team Repository

```bash
skills-orchestrator init --template team-standard
```

This creates `config/skills.yaml`, starter skills, a review pipeline, a GitHub Actions workflow,
and an `evidence/` directory. Existing repositories with skills can still use
`skills-orchestrator init --non-interactive`.

## 3. Check Skills Locally

```bash
skills-orchestrator check --config config/skills.yaml
skills-orchestrator check --config config/skills.yaml --format json
skills-orchestrator check --config config/skills.yaml --format sarif
skills-orchestrator schema validate --kind config --input config/skills.yaml
```

Use `--fail-on warning` when the repository is ready to treat warnings as blocking.

## 4. Lock And Review Drift

```bash
skills-orchestrator build --config config/skills.yaml --lock
skills-orchestrator check --config config/skills.yaml --check-lock skills.lock.json
```

Commit or regenerate `skills.lock.json` consistently across the organization.

## 5. Add CI

```yaml
permissions:
  contents: read
  security-events: write
  pull-requests: write

jobs:
  skills:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: BambooGap/skills-orchestrator@v3.0.0
        with:
          config: config/skills.yaml
          check-lock: skills.lock.json
          upload-sarif: true
          comment-registry-diff: true
```

See [docs/github-action.md](docs/github-action.md) for all inputs.

## 6. Export Release Evidence

```bash
skills-orchestrator manifest --config config/skills.yaml --format json \
  --include-diagnostics --output instruction-manifest.json
skills-orchestrator manifest --config config/skills.yaml --format cyclonedx \
  --output instruction-manifest.cdx.json
skills-orchestrator policy export --config config/skills.yaml --format opa-input \
  --output policy-input.json
skills-orchestrator schema validate --kind manifest --input instruction-manifest.json
skills-orchestrator schema validate --kind policy-opa-input --input policy-input.json
skills-orchestrator registry diff registry-before.json registry-after.json \
  --format markdown --output registry-diff.md
skills-orchestrator registry comment-body registry-diff.md --output registry-diff-comment.md
skills-orchestrator supply-chain sbom --output package-sbom.cdx.json
skills-orchestrator adapters inspect --format json > adapter-inspect.json
```

See [docs/manifest-policy-exports.md](docs/manifest-policy-exports.md).

## 7. Enable Runtime Routing

```bash
skills-orchestrator serve --config config/skills.yaml
```

At every new task boundary, call `prepare_context`. The response includes active skills, inactive
skills, and a structured decision record with routing and content hashes.

Enable opt-in runtime audit when a team needs usage evidence:

```bash
skills-orchestrator serve --config config/skills.yaml --audit-dir .skills-audit
skills-orchestrator usage report --audit-dir .skills-audit
```

## 8. Use Pipelines When Workflow State Matters

```bash
skills-orchestrator pipeline list --config config/skills.yaml
skills-orchestrator pipeline start quick-fix --config config/skills.yaml
skills-orchestrator pipeline status
skills-orchestrator pipeline list-runs
```

Pipeline gates can require one artifact key or a list of keys through `must_produce`.
