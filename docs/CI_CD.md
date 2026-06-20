# CI/CD Integration

## GitHub Action

```yaml
permissions:
  contents: read
  security-events: write

jobs:
  skills:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: BambooGap/skills-orchestrator@v2.6.0
        with:
          config: config/skills.yaml
          policy-pack: builtin/team-standard
          check-lock: skills.lock.json
          upload-sarif: true
```

`upload-sarif: true` requires `security-events: write`. Use `upload-sarif: false` or omit the
option if Code Scanning is not enabled.

## Plain CLI

```bash
python -m pip install skills-orchestrator
skills-orchestrator check --config config/skills.yaml --format json
skills-orchestrator check --config config/skills.yaml --check-lock skills.lock.json
```

## Docker

```bash
docker build -t skills-orchestrator:local .
docker run --rm -v "$PWD:/workspace" -w /workspace \
  skills-orchestrator:local check --config config/skills.yaml
```

## Release Evidence

For a release or audit bundle, generate:

```bash
skills-orchestrator check --config config/skills.yaml --format sarif \
  > skills-orchestrator.sarif
skills-orchestrator manifest --config config/skills.yaml --format json \
  --output instruction-manifest.json
skills-orchestrator manifest --config config/skills.yaml --format cyclonedx \
  --output instruction-manifest.cdx.json
skills-orchestrator policy export --config config/skills.yaml --format opa-input \
  --output policy-input.json
```
