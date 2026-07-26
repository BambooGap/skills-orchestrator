# Skills Orchestrator

[![PyPI](https://img.shields.io/pypi/v/skills-orchestrator.svg)](https://pypi.org/project/skills-orchestrator/)
[![CI](https://github.com/BambooGap/skills-orchestrator/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/BambooGap/skills-orchestrator/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/BambooGap/skills-orchestrator)](https://github.com/BambooGap/skills-orchestrator/releases/latest)
[![License: MIT OR Apache-2.0](https://img.shields.io/badge/License-MIT%20OR%20Apache--2.0-blue.svg)](#license)

**Govern, audit, and ship AI-agent skills.**

Skills Orchestrator turns Markdown instructions into versioned, policy-checked assets that teams
can review in CI and deliver to agent runtimes.

- **Govern:** metadata, zones, policy packs, registries, and deterministic conflict checks.
- **Verify:** SARIF, SBOM, provenance, release attestations, and evidence bundles.
- **Integrate:** GitHub Actions, MCP, and adapters for common agent environments.

[Quick start](#quick-start) · [Documentation](docs/INDEX.md) ·
[Production guide](docs/production-adoption.md) ·
[Latest release](https://github.com/BambooGap/skills-orchestrator/releases/latest)

## Quick start

Requires Python 3.12 or newer.

```bash
python3.12 -m pip install skills-orchestrator

skills-orchestrator init --template team-standard
skills-orchestrator check --config config/skills.yaml
skills-orchestrator build --config config/skills.yaml --lock
```

The starter kit creates a working config, example skills, CI workflow, and evidence directory.
Run the stricter policy pack when the baseline is clean:

```bash
skills-orchestrator check \
  --config config/skills.yaml \
  --policy-pack builtin/engineering-grade \
  --fail-on warning
```

Use the optional MCP runtime only when an agent needs task-scoped skill loading:

```bash
python3.12 -m pip install "skills-orchestrator[mcp]"
skills-orchestrator serve --config config/skills.yaml
```

See [Install](docs/install.md), [GitHub Action](docs/github-action.md), and
[Docker Usage](docs/docker.md) for deployment-specific instructions.

## What it solves

| Need | Skills Orchestrator surface |
| --- | --- |
| Enforce ownership, lifecycle, license, and provenance | Policy packs and stable rule IDs |
| Detect duplicate, conflicting, or drifting instructions | Resolver, lock file, and registry diff |
| Review findings in CI | JSON, SARIF, and reviewer summaries |
| Inventory instruction assets | Native manifest and CycloneDX SBOM |
| Retain audit evidence | Evidence bundles, hash ledger, and release attestations |
| Deliver only task-relevant context | MCP routing with active/inactive skill decisions |
| Coordinate governed multi-step work | Pipelines with artifact and evidence gates |
| Reach existing agent environments | AGENTS.md, Claude Skills, MCP, and SDK adapters |

Skills Orchestrator is a governance and delivery layer. It does not replace an agent runtime,
evaluate model reasoning, or act as a security sandbox.

## Operating model

```text
Markdown skills
      │
      ▼
metadata + policy checks ──► JSON / SARIF / SBOM
      │
      ├──► AGENTS.md and adapter exports
      ├──► registry and evidence bundles
      └──► MCP task routing and pipelines
```

| Layer | Purpose | Main commands |
| --- | --- | --- |
| Static governance | Validate metadata, conflicts, policies, and lock drift | `check`, `validate`, `build --lock` |
| Inventory and proof | Export manifests, policy inputs, registries, and evidence | `manifest`, `policy export`, `registry`, `evidence` |
| Runtime delivery | Select and load governed skills for the current task | `serve`, `mcp-test` |
| Workflow state | Advance gated, resumable multi-step processes | `pipeline start`, `pipeline advance` |
| Ecosystem delivery | Generate or inspect downstream agent surfaces | `adapters`, `sync` |

The authoritative contracts are [SPEC.md](SPEC.md), [CONFORMANCE.md](CONFORMANCE.md), and the
packaged schemas. Runtime details live in [MCP Server](docs/MCP_SERVER.md),
[Pipelines](docs/PIPELINES.md), and [Adapters](docs/adapters.md).

## CI and production adoption

Start with advisory checks. Promote to blocking gates only after the findings, registry diff, and
review artifacts are useful to maintainers.

```yaml
permissions:
  contents: read
  security-events: write
  pull-requests: write

steps:
  - uses: actions/checkout@<reviewed-commit-sha>
  - uses: BambooGap/skills-orchestrator@<release-commit-sha>
    with:
      config: config/skills.yaml
      policy-pack: builtin/team-standard
      upload-sarif: true
      reviewer-summary: true
```

Production consumers should pin the exact PyPI version, GitHub Action release commit SHA, Docker
digest, and dependency hashes. Do not automatically follow the newest tag. The complete rollout
sequence is documented in [Production Adoption](docs/production-adoption.md) and the
[Adoption Playbook](docs/adoption-playbook.md).

## Evidence and interoperability

The CLI produces machine-readable artifacts instead of requiring downstream systems to parse
console output or Markdown:

| Artifact | Typical consumer |
| --- | --- |
| Check JSON and SARIF | CI, code scanning, reviewer automation |
| Instruction manifest and CycloneDX | Inventory and supply-chain systems |
| OPA input and Rego test fixture | Policy review and external enforcement |
| Registry graph and diff | Platform teams and multi-repository governance |
| Evidence manifest and bundle hash | Auditors, release owners, hosted consumers |
| Adapter inspection and exports | Agent runtimes and integration teams |

See [Manifest and Policy Exports](docs/manifest-policy-exports.md),
[Registry and Evidence](docs/registry-evidence.md), and
[Supply Chain Verification](docs/supply-chain-verification.md).

## Documentation

| Goal | Start here |
| --- | --- |
| Add checks to one repository | [Install](docs/install.md), [GitHub Action](docs/github-action.md) |
| Roll out across a team | [Production Adoption](docs/production-adoption.md), [Team Standardization](docs/team-standardization.md) |
| Review security and provenance | [Policy Packs](docs/policy-packs.md), [Supply Chain Verification](docs/supply-chain-verification.md) |
| Integrate an agent runtime | [MCP Server](docs/MCP_SERVER.md), [Adapters](docs/adapters.md), [Pipelines](docs/PIPELINES.md) |
| Implement compatible tooling | [SkillOps Contract](SPEC.md), [Conformance](CONFORMANCE.md), [Third-party Implementation](docs/third-party-implementation.md) |
| Evaluate adoption or commercial boundaries | [Adoption Maturity Model](docs/adoption-maturity-model.md), [Open-core Boundary](docs/open-core-boundary.md) |

The [Documentation Index](docs/INDEX.md) contains the complete role-based map, examples, schemas,
operations guides, and external-consumer contracts.

## Release verification boundary

The release contract is strict: a Git tag or the version in the source tree is not a public-release claim.
A version is consumable only after its GitHub Release, PyPI package, and GHCR image are available
and Release Integrity has passed.

- [GitHub latest release](https://github.com/BambooGap/skills-orchestrator/releases/latest)
- [PyPI project](https://pypi.org/project/skills-orchestrator/)
- [GHCR package](https://github.com/BambooGap/skills-orchestrator/pkgs/container/skills-orchestrator)
- [Post-release Smoke](https://github.com/BambooGap/skills-orchestrator/actions/workflows/post-release-smoke.yml)
- [Release Integrity](https://github.com/BambooGap/skills-orchestrator/actions/workflows/release-integrity.yml)
- [Supply Chain Verification](docs/supply-chain-verification.md)

The project produces SLSA readiness and evidence inputs. 它不是正式 SLSA 等级认证，也不声明
已经达到 SLSA Build L3+. See [SLSA Readiness](docs/slsa-readiness.md) for the exact boundary.

Published tags are immutable release snapshots. Documentation improvements land on `main` and
appear in a future release; existing tags are not moved to rewrite their history.

## Contributing and support

```bash
git clone https://github.com/BambooGap/skills-orchestrator
cd skills-orchestrator
python3.12 -m pip install -c constraints.txt -e ".[dev]"
pytest tests/ -q
ruff check skills_orchestrator/ tests/
```

Read [Contributing](CONTRIBUTING.md), [Security](SECURITY.md), [Governance](GOVERNANCE.md),
[Support](SUPPORT.md), [Code of Conduct](CODE_OF_CONDUCT.md), and
[Third-party Notices](THIRD_PARTY_NOTICES.md) before opening a change or report.

External adoption and public references require explicit permission; see
[Adoption Authorization](docs/adoption-authorization.md).

## License

Licensed under either [MIT](LICENSE) or [Apache-2.0](LICENSE-APACHE), at your option.
