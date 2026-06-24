# Skills Orchestrator Roadmap: SkillOps for Agent Instructions

> Status: v3.0.0 open-core slice: PR registry diff automation, package SBOM, CodeQL/GHCR
> workflows, adapter inspection/scaffolds, and commercial handoff contracts.
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
| GitHub Actions | Low-friction adoption | One-step CI action with SARIF and PR registry diff comment |
| PyPI | Python CLI distribution | Trusted Publishing from GitHub Release |
| CycloneDX / SPDX | Supply-chain vocabulary | Instruction manifest CycloneDX and package SBOM |
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

Status: implemented for v2.3.0.

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

Status: implemented for v2.3.0.

Goal: make instruction inventories visible to external supply-chain tools.

Deliver:

- Keep `skills.lock.json` as the local reproducibility lock.
- `manifest --format json` for the native instruction manifest.
- `manifest --format cyclonedx` as experimental output.
- Defer SPDX until field mapping and consumer behavior are tested.

Do not claim GitHub Dependency Graph or Dependency-Track support until tested with real output.

## Phase 3: Policy Export

Status: implemented for v2.3.0.

Goal: connect to policy-as-code without replacing the current resolver.

Deliver:

- `policy export --format opa-input`.
- `policy export --format rego-test`.
- Examples proving `conflict_with`, `priority`, `load_policy`, and `zones` can be expressed as
  policy fixtures.

Do not add OPA as a runtime backend yet. The existing resolver is the authoritative decision
system; OPA should be a proof and integration surface, not a second source of truth.

## Phase 4: Distribution Hardening

Status: implemented across v2.4.0-v4.4.0 for Docker smoke, package SBOM, CodeQL, GHCR release
push, pinned third-party Actions, PyPI artifact attestation, digest-bound container
SBOM/provenance attestation, and local release artifact verification.

Goal: remove adoption friction for enterprise and CI users.

Deliver:

- Docker image for the CLI.
- GitHub Action pinned to released versions.
- Third-party workflow actions pinned to commit SHAs.
- `constraints.txt` for the action/CI/publish runtime dependency set.
- GitHub artifact attestation for wheel and sdist during publishing.
- Python package SBOM through `supply-chain sbom`.
- Container image SBOM/provenance through `supply-chain container-release`.
- Local container release artifact verification through `supply-chain verify-container-release`.
- CodeQL workflow.
- GHCR release publishing workflow.
- Release checklist that verifies GitHub Release, PyPI, wheel, sdist, CLI version, and package
  metadata.
- GitHub Artifact Attestations for GHCR image provenance and SBOM, bound to the pushed digest.

Python remains acceptable for the core CLI. Rewriting in Go or Rust is not the next bottleneck;
distribution and CI integration are.

## Phase 6: Team Standardization And Runtime Governance

Status: implemented across v2.4.0 and v2.5.x.

Goal: move from advisory docs to a team-standard product loop.

Delivered:

- Team standardization guide and role-based documentation index.
- Structured `prepare_context` decision records with routing ID, task hash, registry generation,
  active/inactive skills, and content hashes.
- Opt-in MCP audit JSONL and `usage report`.
- MCP `pipeline_list_runs`.
- Pipeline gates that support multiple required artifacts.
- Built-in `builtin/team-standard` policy pack for owner/source/version/lifecycle/approver fields.
- `doctor`, `registry build`, `registry diff`, `evidence export`, and `integrations list`.
- Configurable runtime skill-content byte limits.
- Optional HMAC task hashing for MCP audit logs.
- Pipeline context redaction before state persistence.

Next:

- Hash-locked dependency install after the constraints workflow is stable.
- Image signing after digest-bound attestation has been exercised across releases.
- SPDX mapping only after a real downstream consumer is tested.

## Phase 7: PR Review Automation

Status: implemented in v3.0.0.

Goal: make registry changes visible inside pull requests without requiring a hosted service.

Delivered:

- Action inputs for `registry-diff`, `registry-config-glob`, `registry-base-ref`,
  `registry-diff-file`, and `comment-registry-diff`.
- `registry comment-body` for stable comment Markdown with a hidden idempotency marker.
- GitHub PR comment upsert in an integration module, not the registry core.
- Documentation for `pull-requests: write` and avoiding `pull_request_target` by default.

## Phase 8: Ecosystem Adapters

Status: implemented across v3.0.0-v4.4.0 as inspection, scaffold generation, Claude Skills export,
and adapter evidence fixtures.

Goal: connect to AGENTS.md, Claude Skills, MCP clients, and OpenAI Agents SDK without claiming to
own their standards.

Delivered:

- `adapters inspect` for AGENTS.md, Claude Skills, MCP client configs, and OpenAI Agents SDK
  dependency detection.
- `adapters export mcp-client-config`.
- `adapters export openai-agents-sdk`.
- `adapters export claude-skills` with governance metadata preserved in generated `*/SKILL.md`
  bundles.
- Adapter inspection JSON Schema.
- Claude Skills export unit coverage.
- `examples/adapter-evidence/` as an executable fixture for Claude Skills export, MCP client
  config, OpenAI Agents SDK scaffold, and adapter inspection evidence.

Next:

- More real ecosystem adapter examples once downstream projects need them.
- Optional construction test when OpenAI Agents SDK is installed.

## Phase 9: Open-core Commercial Contracts

Status: implemented in v3.0.0 as docs, schemas, and examples.

Goal: make future GitHub App, hosted registry, and dashboard products consume OSS artifacts instead
of forking semantics.

Delivered:

- Open-core boundary documentation.
- GitHub App, hosted registry, and enterprise dashboard blueprints.
- JSON Schema contracts for installation, ingest, dashboard snapshots, and dashboard rollups.
- `examples/commercial-handoff/` sample payloads.

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
