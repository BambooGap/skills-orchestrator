# GitHub Action

Use this action to run `skills-orchestrator check` in CI. For first-time adoption, start with
[Adoption Playbook](adoption-playbook.md) and keep the first workflow advisory until reviewers
understand SARIF and registry diff output.

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
      - uses: BambooGap/skills-orchestrator@v3.3.0
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
      - uses: BambooGap/skills-orchestrator@v3.3.0
        with:
          config: config/skills.yaml
          policy-pack: builtin/team-standard
          upload-sarif: true
```

Private and internal repositories may require GitHub Code Security to be enabled before SARIF
uploads are accepted.

The action installs the local action source with `constraints.txt`, so the CLI runtime dependency
set is constrained for a given action revision. It is not a hash-locked install yet.

## Registry Diff PR Comment

For pull requests, the action can compare the base and head registry snapshots, generate a Markdown
review artifact, and update one idempotent PR comment. The CLI still owns only file generation; the
GitHub API call lives in the Action integration boundary.

```yaml
name: Skill registry review

on:
  pull_request:
    branches: [main]

permissions:
  contents: read
  pull-requests: write

jobs:
  skills:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: BambooGap/skills-orchestrator@v3.3.0
        with:
          config: config/skills.yaml
          registry-diff: true
          comment-registry-diff: true
```

`comment-registry-diff: true` also generates the registry diff artifact. The comment uses the hidden
marker `<!-- skills-orchestrator:registry-diff-comment:v1 -->`, so repeat runs update the previous
comment instead of posting duplicates. Do not use `pull_request_target` unless you have separately
reviewed the security implications for untrusted fork code.

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

## Marketplace Readiness

`action.yml` includes the `branding` metadata GitHub uses for Marketplace action cards. The
repository can be used directly with a release tag, for example
`BambooGap/skills-orchestrator@v3.3.0`, even before the Marketplace listing is public.

Recommended Marketplace positioning:

- Name: `Skills Orchestrator Check`
- Primary category: code quality
- Secondary category: security
- Short description: `Enforce SkillOps policy packs, SARIF, registry diff, and evidence checks for AI-agent skills.`
- First example: the advisory workflow above, not the strict engineering gate.

GitHub Marketplace listing is a separate release UI step, not something `gh release create`
publishes automatically. GitHub's documented flow is to open the repository `action.yml`, draft a
release from the Marketplace banner, select **Publish this Action to the GitHub Marketplace**, pick
Marketplace categories, and publish the release. The owner account may also need to accept the
GitHub Marketplace Developer Agreement before the checkbox is enabled.

Reference: [Publishing actions in GitHub Marketplace](https://docs.github.com/actions/creating-actions/publishing-actions-in-github-marketplace).

## Inputs

| Input | Default | Description |
| --- | --- | --- |
| `config` | `config/skills.yaml` | Path to `skills.yaml`. |
| `zone` | empty | Optional zone id. |
| `check-lock` | empty | Optional `skills.lock.json` path to check for drift. |
| `format` | `text` | Output format when `upload-sarif` is false: `text`, `json`, or `sarif`. |
| `fail-on` | `error` | Exit threshold: `error`, `warning`, or `never`. |
| `max-skill-bytes` | `20000` | Threshold for SO005 oversized-skill diagnostics. |
| `policy-pack` | empty | Optional built-in or local declarative policy pack, for example `builtin/team-standard` or `builtin/engineering-grade`. |
| `upload-sarif` | `false` | Upload SARIF to GitHub Code Scanning. |
| `sarif-file` | `skills-orchestrator.sarif` | SARIF file path used for uploads. |
| `registry-diff` | `false` | Generate a base-vs-head registry diff Markdown artifact. |
| `registry-config-glob` | `config/skills.yaml` | Newline-separated registry config globs. |
| `registry-base-ref` | empty | Optional git ref for the base registry snapshot. |
| `registry-diff-file` | `registry-diff.md` | Relative filename for the generated Markdown artifact. |
| `comment-registry-diff` | `false` | Update the pull request registry diff comment. Requires `pull-requests: write`. |

## Outputs

| Output | Description |
| --- | --- |
| `registry-diff-file` | Absolute path to the generated registry diff Markdown file. |
| `registry-comment-body` | Absolute path to the generated PR comment body Markdown file. |
