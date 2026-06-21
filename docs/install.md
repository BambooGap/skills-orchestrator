# Install

Skills Orchestrator requires Python 3.12 or newer.

## PyPI

```bash
python3.12 -m pip install skills-orchestrator
skills-orchestrator --version
```

## pipx

```bash
pipx install skills-orchestrator --python python3.12
skills-orchestrator --version
```

## uvx

```bash
uvx --python 3.12 skills-orchestrator --version
```

## GitHub Action

Use the action when the repo should enforce skill checks in CI:

```yaml
permissions:
  contents: read
  security-events: write

jobs:
  skills:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: BambooGap/skills-orchestrator@v3.0.0
        with:
          config: config/skills.yaml
          policy-pack: builtin/team-standard
          check-lock: skills.lock.json
          upload-sarif: true
```

See [GitHub Action](github-action.md) for inputs and SARIF permissions.

## Docker

Use Docker when CI hosts should not install Python packages directly:

```bash
docker run --rm ghcr.io/bamboogap/skills-orchestrator:v3.0.0 --version

docker build -t skills-orchestrator:local .
docker run --rm -v "$PWD:/workspace" -w /workspace \
  skills-orchestrator:local check --config config/skills.yaml
```

See [Docker Usage](docker.md) for more examples.

## Local Development

```bash
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev]' -c constraints.txt
pytest
```

The project also supports Python 3.13 in CI.
