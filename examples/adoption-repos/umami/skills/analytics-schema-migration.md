---
id: analytics-schema-migration
name: Analytics Schema Migration
summary: Review database migrations that affect analytics events, sessions, or rollups.
tags: [database, migration, analytics]
load_policy: free
priority: 85
zones: [default]
conflict_with: []
owner: database-team
source: repo://examples/adoption-repos/umami/skills/analytics-schema-migration.md
version: 1.0.0
lifecycle: active
reviewed_at: 2026-06-22
expires_at: 2026-12-22
license: MIT
---
# Analytics Schema Migration

Use this skill before merging analytics schema migrations.

## Checklist

- Confirm migration order is deterministic and reversible where possible.
- Check whether old event writers remain compatible during rollout.
- Validate index changes against query paths used by dashboards.
- Require a backfill or no-backfill decision in the pull request.
