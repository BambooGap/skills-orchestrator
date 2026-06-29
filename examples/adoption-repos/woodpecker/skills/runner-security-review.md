---
id: runner-security-review
name: Runner Security Review
summary: Review runner configuration, isolation, and trust boundary changes.
tags: [security, runner, ci]
load_policy: free
priority: 95
zones: [default]
conflict_with: []
owner: security-team
source: repo://examples/adoption-repos/woodpecker/skills/runner-security-review.md
version: 1.0.0
lifecycle: active
reviewed_at: 2026-06-22
expires_at: 2026-12-22
license: MIT
---
# Runner Security Review

Use this skill when runner images, isolation, or scheduling rules change.

## Checklist

- Confirm untrusted jobs cannot access privileged runners.
- Check workspace cleanup and credential revocation behavior.
- Verify runner labels match the intended trust boundary.
- Require a rollback path for runner pool changes.
