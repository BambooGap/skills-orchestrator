---
id: release-observability
name: Release Observability
summary: Review release monitoring, rollback signals, and dashboard coverage for analytics changes.
tags: [release, observability, analytics]
load_policy: free
priority: 80
zones: [default]
conflict_with: []
owner: platform-team
source: repo://examples/adoption-repos/umami/skills/release-observability.md
version: 1.0.0
lifecycle: active
reviewed_at: 2026-06-22
expires_at: 2026-12-22
license: MIT
---
# Release Observability

Use this skill when a release changes analytics ingestion or reporting.

## Checklist

- Confirm the release has an error-rate or ingestion-lag signal.
- Check that dashboard changes have a sample-size sanity check.
- Require rollback criteria for migrations or event-shape changes.
- Document any expected metric discontinuity.
