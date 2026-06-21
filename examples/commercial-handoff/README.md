# Commercial Handoff Contracts

This directory contains example payloads for future hosted or enterprise surfaces.
They are not SaaS implementations. The open-source CLI remains the source of truth
for generating registry, evidence, schema, and adapter artifacts.

Validate the examples:

```bash
skills-orchestrator schema validate \
  --kind github-app-installation \
  --input examples/commercial-handoff/installation.json

skills-orchestrator schema validate \
  --kind hosted-registry-ingest \
  --input examples/commercial-handoff/registry-ingest.json

skills-orchestrator schema validate \
  --kind enterprise-dashboard-snapshot \
  --input examples/commercial-handoff/dashboard-snapshot.json
```

Boundary:

- GitHub App code, installation tokens, billing, tenants, and databases are not part of the OSS core.
- Hosted services should ingest files produced by this CLI instead of redefining registry semantics.
- Dashboards should render derived state from evidence artifacts, not become a second policy engine.
