# Hosted Registry Blueprint

The hosted registry is a downstream consumer of OSS-generated artifacts. It should not become a
second registry implementation.

## Ingest Contract

The minimum ingest payload points to artifacts produced by the CLI:

- `skill-registry.json`
- optional `registry-diff.json`
- `evidence-manifest.json`
- optional `doctor.json`
- optional `adapter-inspect.json`
- optional `multi-repo-artifacts.json` for organization-level rollout views

Validate the contract:

```bash
skills-orchestrator schema validate \
  --kind hosted-registry-ingest \
  --input examples/commercial-handoff/registry-ingest.json
```

For an adoption-focused static fixture, validate:

```bash
skills-orchestrator schema validate \
  --kind hosted-registry-ingest \
  --input examples/external-consumer/hosted-registry-ingest.json

skills-orchestrator schema validate \
  --kind multi-repo-artifacts \
  --input examples/external-consumer/multi-repo-artifacts.json
```

## Identity

Store source identity separately from registry semantics:

- repository full name,
- ref,
- commit SHA,
- installation id when a GitHub App is used,
- snapshot id,
- created timestamp.

## Retention

Recommended retention tiers:

| Tier | Retention | Purpose |
| --- | --- | --- |
| PR snapshots | 30-90 days | Review history and comment recovery. |
| Default branch snapshots | 1 year | Governance trend reporting. |
| Release evidence | Customer policy | Audit and contractual retention. |

## Redaction

The hosted layer should prefer metadata and hashes. Avoid uploading raw skill content unless the
customer explicitly enables that mode.

Required redaction defaults:

- redact local absolute paths,
- exclude raw MCP task text,
- exclude secrets and tokens,
- retain content hashes for correlation.

## Export

Enterprise users must be able to export the same artifact contracts they ingest. Lock-in should be
operational convenience, not private data format control.
