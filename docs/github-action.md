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
      - uses: BambooGap/skills-orchestrator@v2.5.0
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
      - uses: BambooGap/skills-orchestrator@v2.5.0
        with:
          config: config/skills.yaml
          policy-pack: builtin/team-standard
          upload-sarif: true
```

Private and internal repositories may require GitHub Code Security to be enabled before SARIF
uploads are accepted.

The action installs the local action source with `constraints.txt`, so the CLI runtime dependency
set is constrained for a given action revision. It is not a hash-locked install yet.

## Hardened Pinning

For high-trust repositories, pin both checkout and this action to full commit SHAs. Keep the simple
tag example for onboarding, but use SHA pins in protected production repos:

```yaml
permissions:
  contents: read
  security-events: write

jobs:
  skills:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683
      - uses: BambooGap/skills-orchestrator@<full-release-commit-sha>
        with:
          config: config/skills.yaml
          check-lock: skills.lock.json
          policy-pack: builtin/team-standard
          fail-on: warning
          upload-sarif: true
```

`upload-sarif: true` requires `security-events: write`.

## Inputs

| Input | Default | Description |
| --- | --- | --- |
| `config` | `config/skills.yaml` | Path to `skills.yaml`. |
| `zone` | empty | Optional zone id. |
| `check-lock` | empty | Optional `skills.lock.json` path to check for drift. |
| `format` | `text` | Output format when `upload-sarif` is false: `text`, `json`, or `sarif`. |
| `fail-on` | `error` | Exit threshold: `error`, `warning`, or `never`. |
| `max-skill-bytes` | `20000` | Threshold for SO005 oversized-skill diagnostics. |
| `policy-pack` | empty | Optional built-in policy pack, for example `builtin/team-standard`. |
| `upload-sarif` | `false` | Upload SARIF to GitHub Code Scanning. |
| `sarif-file` | `skills-orchestrator.sarif` | SARIF file path used for uploads. |
