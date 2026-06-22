---
id: analytics-privacy-review
name: Analytics Privacy Review
summary: Review tracking changes for privacy, retention, and user-visible data boundaries.
tags: [privacy, analytics, review]
load_policy: free
priority: 95
zones: [default]
conflict_with: []
owner: data-platform
source: repo://examples/pilot-repos/umami/skills/analytics-privacy-review.md
version: 1.0.0
lifecycle: active
reviewed_at: 2026-06-22
expires_at: 2026-12-22
license: MIT
---
# Analytics Privacy Review

Use this skill when events, identifiers, retention rules, or exports change.

## Checklist

- Confirm new event fields do not include direct personal identifiers.
- Verify retention and deletion behavior are unchanged or documented.
- Check whether dashboards expose tenant or workspace boundaries correctly.
- Require release notes when tracking semantics change.
