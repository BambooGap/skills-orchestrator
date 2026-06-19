# Skills Orchestrator Roadmap: Agent Instruction Supply Chain

> Version: 2026-06 final execution plan
>
> Goal: evolve Skills Orchestrator from a compile-time skill governance tool into a practical
> Agent Instruction Supply Chain utility, without replacing existing Linux Foundation or CNCF
> projects.

## Positioning

Skills Orchestrator should remain a glue layer. It should not define a competing skill format,
policy runtime, SBOM standard, or agent protocol.

The durable product role is:

> Govern agent instructions by checking provenance, conflicts, policy, routing, and distribution
> across coding-agent surfaces.

The practical entry point remains:

```bash
skills-orchestrator check .
```

Everything else should make that command easier to trust, automate, or integrate.

## Phase 1: Diagnostics And Machine-Readable Output

Scope:

- Add a dedicated `check` command.
- Introduce a shared `Diagnostic` model for check findings.
- Add `--format text|json|sarif`.
- Keep existing `validate` and `build` text behavior compatible.
- Treat SARIF as a GitHub Code Scanning projection of diagnostics, not the internal source of
  truth.

Initial rule set:

| Rule | Name | Severity | Notes |
| --- | --- | --- | --- |
| SO001 | missing-description | warning | Missing `summary` / official `description`. |
| SO002 | duplicate-skill-id | warning | Warning first because parser currently keeps first-seen ids. |
| SO003 | unresolved-conflict | error | Resolver cannot decide a declared conflict. |
| SO004 | asymmetric-conflict-declaration | warning | One-way conflicts are valid today, but weaker for auditability. |
| SO005 | oversized-skill | info | Flags large skill files before they become context-heavy. |
| SO007 | lock-drift | warning | Existing lock differs from current resolved state. |

Deferred:

- Unsafe instruction pattern detection. There is no stable public standard yet, so this should
  not be claimed as an authoritative security rule.

## Phase 2: GitHub Action And Code Scanning

Scope:

- Publish a GitHub Action after Phase 1 output formats are stable.
- The action should support optional SARIF upload through `upload-sarif: true`.
- README must show required permissions explicitly:

```yaml
permissions:
  contents: read
  security-events: write
```

Default behavior:

- `upload-sarif: false` by default to avoid hidden permission failures.
- Documentation should present a complete Code Scanning example using `upload-sarif: true`.

Implementation note:

- Start with a composite action that installs the PyPI package.
- Docker action can follow later for stricter enterprise/offline distribution.

## Phase 3: Instruction Manifest

Scope:

- Keep `skills.lock.json` as the project-local reproducibility lock.
- Add `manifest --format json` for a native instruction manifest.
- Add `manifest --format cyclonedx` as experimental external-tooling output.

Do not claim GitHub Dependency Graph support unless tested.

CycloneDX is the first external format because its BOM model is more flexible for non-code
assets. SPDX can follow once field mapping is proven.

## Phase 4: OPA/Rego Proof, Not Runtime Replacement

Scope:

- Add `policy export --format opa-input`.
- Add `policy export --format rego-test`.
- Do not add OPA as a runtime decision backend.

Reason:

The current `conflict_with + priority + load_policy + zones` model is already the authoritative
decision system. OPA integration should prove that these decisions can be expressed as
policy-as-code, not create a second source of truth.

## Phase 5: Community Narrative

Write externally only after the tool has a working integration path:

- `check`
- JSON/SARIF
- GitHub Action

Suggested title:

> Agent Instructions Need a Supply Chain

The article should include real output from this repository rather than only conceptual framing.

## Current Release Constraint

Local implementation, tests, and commits can be completed in this workspace.

GitHub push, GitHub Release creation, and PyPI release require valid GitHub authentication. At
the time this roadmap was written, `gh auth status` reported invalid local tokens for the
configured GitHub accounts, so remote release operations are blocked until re-authentication.
