# GitHub Action

Use this action to run `skills-orchestrator check` in CI.

The action installs Skills Orchestrator from the checked-out action source, so pinning the action
version also pins the CLI implementation:

```yaml
name: Skill checks

on:
  pull_request:
  push:
    branches: [main]

jobs:
  skills:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: BambooGap/skills-orchestrator@v2.2.0
        with:
          config: config/skills.yaml
```

## Code Scanning

To upload SARIF to GitHub Code Scanning, grant `security-events: write` and set
`upload-sarif: true`.

```yaml
name: Skill code scanning

on:
  pull_request:
  push:
    branches: [main]

permissions:
  contents: read
  security-events: write

jobs:
  skills:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: BambooGap/skills-orchestrator@v2.2.0
        with:
          config: config/skills.yaml
          upload-sarif: true
```

Private and internal repositories may require GitHub Code Security to be enabled before SARIF
uploads are accepted.

## Inputs

| Input | Default | Description |
| --- | --- | --- |
| `config` | `config/skills.yaml` | Path to `skills.yaml`. |
| `zone` | empty | Optional zone id. |
| `check-lock` | empty | Optional `skills.lock.json` path to check for drift. |
| `format` | `text` | Output format when `upload-sarif` is false: `text`, `json`, or `sarif`. |
| `fail-on` | `error` | Exit threshold: `error`, `warning`, or `never`. |
| `max-skill-bytes` | `20000` | Threshold for SO005 oversized-skill diagnostics. |
| `upload-sarif` | `false` | Upload SARIF to GitHub Code Scanning. |
| `sarif-file` | `skills-orchestrator.sarif` | SARIF file path used for uploads. |
