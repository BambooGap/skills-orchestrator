---
id: alert-delivery-release
name: Alert Delivery Release Gate
summary: Gate notification, webhook, and escalation changes before production rollout.
tags: [release, ci, notifications]
load_policy: free
priority: 85
zones: [default]
conflict_with: []
owner: platform-team
source: repo://examples/adoption-repos/healthchecks/skills/alert-delivery-release.md
version: 1.0.0
lifecycle: active
reviewed_at: 2026-06-22
expires_at: 2026-12-22
license: MIT
---
# Alert Delivery Release Gate

Use this skill before merging changes that affect alert delivery.

## Checklist

- Confirm delivery channels are covered by tests or a smoke check.
- Check whether webhook payload shape changes are backward compatible.
- Confirm release notes mention user-visible delivery behavior.
- Require rollback instructions for notification provider migrations.
