# CI/CD Integration

## GitHub Action

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
      - uses: BambooGap/skills-orchestrator@v4.8.38
        with:
          config: config/skills.yaml
          policy-pack: builtin/team-standard
          check-lock: skills.lock.json
          upload-sarif: true
          comment-registry-diff: true
```

`upload-sarif: true` requires `security-events: write`. Use `upload-sarif: false` or omit the
option if Code Scanning is not enabled.
`comment-registry-diff: true` requires `pull-requests: write` and updates one marker-based PR
comment per pull request.

If the repository requires pinned third-party actions, bootstrap CI with:

```bash
skills-orchestrator init --template team-standard --hardened-workflow
```

The default starter keeps `actions/checkout@v4` for readability; the hardened
starter pins checkout to the audited SHA used by this project.

## Plain CLI

```bash
python3.12 -m pip install skills-orchestrator
skills-orchestrator check --config config/skills.yaml --format json
skills-orchestrator check --config config/skills.yaml --check-lock skills.lock.json
skills-orchestrator conformance run --config config/skills.yaml
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
