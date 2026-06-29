---
id: incident-runbook-review
name: Incident Runbook Review
summary: Review alerting or on-call runbook changes for rollback, escalation, and owner clarity.
tags: [operations, incident, runbook]
load_policy: free
priority: 90
zones: [default]
conflict_with: []
owner: sre-team
source: repo://examples/adoption-repos/healthchecks/skills/incident-runbook-review.md
version: 1.0.0
lifecycle: active
reviewed_at: 2026-06-22
expires_at: 2026-12-22
license: MIT
---
# Incident Runbook Review

Use this skill when a pull request changes alert routing, on-call steps, or
incident response instructions.

## Checklist

- Confirm every alert has an owner and an escalation path.
- Verify rollback steps are concrete and runnable.
- Check that silence windows and false-positive handling are documented.
- Ask for a test alert or dry-run result when delivery behavior changes.
