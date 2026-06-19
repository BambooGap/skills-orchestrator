# Skills Orchestrator Roadmap: SkillOps for Agent Instructions

> Status: v2.2.0 shipped on GitHub and PyPI.
>
> Product direction: make agent instructions checkable, reproducible, routable, and consumable
> by existing CI and supply-chain tooling.

## Product Description

Short description:

> Skills Orchestrator is a SkillOps CLI for governing AI-agent instructions across projects,
> CI, and coding-agent runtimes.

Long description:

> Skills Orchestrator turns scattered Markdown skills into a governed instruction system. It
> checks metadata, duplicate ids, conflict declarations, lock drift, and oversized instructions;
> emits text, JSON, and SARIF reports; builds AGENTS.md bootstrap files; serves skills through
> MCP for runtime routing; and coordinates multi-step workflows through pipelines.

The project should not position itself as a new agent standard, a replacement policy engine, or a
new SBOM format. It should remain the glue layer that makes agent instructions visible to tools
that teams already use.

## Capability Boundary

Own:

- Static instruction diagnostics.
- Runtime skill routing through MCP.
- Reproducible instruction locks.
- Machine-readable reports for CI.
- Distribution to coding-agent surfaces such as AGENTS.md, Cursor, Copilot, Hermes, and OpenClaw.

Do not own:

- A universal skill specification.
- A competing policy runtime.
- A replacement for CycloneDX, SPDX, OPA, SARIF, or GitHub Code Scanning.
- Claims of security-scanner completeness before the rule model is mature.

## Spider-Web Strategy

The durable market path is to connect Skills Orchestrator to established ecosystem surfaces:

| Surface | Role | Practical connection |
| --- | --- | --- |
| GitHub Code Scanning | Developer-facing trust channel | SARIF output from `skills-orchestrator check` |
| GitHub Actions | Low-friction adoption | One-step CI action with optional SARIF upload |
| PyPI | Python CLI distribution | Trusted Publishing from GitHub Release |
| CycloneDX / SPDX | Supply-chain vocabulary | Experimental instruction manifest export |
| OPA / Rego | Policy-as-code vocabulary | Export inputs/tests, not a second runtime backend |
| OpenSSF / LF AI & Data / CNCF | Community and enterprise narrative | Evidence-backed article and integration examples |

## Phase 0: Shipped in v2.2.0

Delivered:

- `skills-orchestrator check`.
- Shared diagnostic model.
- `--format text|json|sarif`.
- `validate --format json|sarif`.
- Rule docs under `docs/rules/`.
- GitHub Release v2.2.0.
- PyPI v2.2.0 through Trusted Publishing.

Initial rules:

| Rule | Name | Severity | Notes |
| --- | --- | --- | --- |
| SO000 | fatal-error | error | Keeps JSON/SARIF valid when parsing fails. |
| SO001 | missing-description | warning | Missing `summary` or official `description`. |
| SO002 | duplicate-skill-id | warning | Parser keeps the first occurrence today. |
| SO003 | unresolved-conflict | error | Resolver cannot decide a declared conflict. |
| SO004 | asymmetric-conflict-declaration | warning | One-way conflicts remain valid but weaker for audit. |
| SO005 | oversized-skill | info | Large skill file deserves review before runtime injection. |
| SO007 | lock-drift | warning | Current resolved skills differ from lock. |

## Phase 1: GitHub Action and Code Scanning

Goal: let another project adopt the checker in one CI block.

Deliver:

- Composite GitHub Action.
- `upload-sarif: true|false` option.
- README examples for normal CI and Code Scanning.
- Permission documentation:

```yaml
permissions:
  contents: read
  security-events: write
```

Default:

- Keep `upload-sarif` explicit. Hidden upload attempts create confusing permission failures.
- Provide a complete one-step example for teams that do want Code Scanning.

## Phase 2: Instruction Manifest

Goal: make instruction inventories visible to external supply-chain tools.

Deliver:

- Keep `skills.lock.json` as the local reproducibility lock.
- Add `manifest --format json` for the native instruction manifest.
- Add `manifest --format cyclonedx` as experimental output.
- Defer SPDX until field mapping and consumer behavior are tested.

Do not claim GitHub Dependency Graph or Dependency-Track support until tested with real output.

## Phase 3: Policy Export

Goal: connect to policy-as-code without replacing the current resolver.

Deliver:

- `policy export --format opa-input`.
- `policy export --format rego-test`.
- Examples proving `conflict_with`, `priority`, `load_policy`, and `zones` can be expressed as
  policy fixtures.

Do not add OPA as a runtime backend yet. The existing resolver is the authoritative decision
system; OPA should be a proof and integration surface, not a second source of truth.

## Phase 4: Distribution Hardening

Goal: remove adoption friction for enterprise and CI users.

Deliver:

- Docker image for the CLI.
- GitHub Action pinned to released versions.
- Release checklist that verifies GitHub Release, PyPI, wheel, sdist, CLI version, and package
  metadata.
- Optional signed provenance only after the release flow is stable.

Python remains acceptable for the core CLI. Rewriting in Go or Rust is not the next bottleneck;
distribution and CI integration are.

## Phase 5: Community Narrative

Write publicly only after the GitHub Action and SARIF path are live.

Suggested article title:

> Agent Instructions Need a Supply Chain

The article should lead with concrete output:

- A 21-skill repository check.
- A SARIF report in GitHub Code Scanning.
- A lock-drift example.
- Why asymmetric conflicts are warnings, not errors.
- How the project complements OpenSSF / LF AI & Data / CNCF surfaces instead of replacing them.

## Release Note

PyPI publication is automated by `.github/workflows/publish.yml`.

Publishing flow:

1. Create a GitHub Release.
2. The `release.published` workflow runs tests and builds the package.
3. `pypa/gh-action-pypi-publish` publishes through PyPI Trusted Publishing using OIDC.

This means maintainers may not need to log in to PyPI or keep a PyPI token locally, but the PyPI
project must keep its Trusted Publisher configuration aligned with the GitHub repository.
