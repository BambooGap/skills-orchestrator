---
id: pipeline-change-review
name: Pipeline Change Review
summary: Review CI pipeline changes for permissions, secrets, and reproducibility.
tags: [ci, pipeline, review]
load_policy: free
priority: 90
zones: [default]
conflict_with: []
owner: ci-platform
source: repo://examples/adoption-repos/woodpecker/skills/pipeline-change-review.md
version: 1.0.0
lifecycle: active
reviewed_at: 2026-06-22
expires_at: 2026-12-22
license: MIT
---
# Pipeline Change Review

Use this skill when pipeline definitions, triggers, or secret access change.

## Checklist

- Confirm secret exposure is limited to trusted events.
- Check that privileged steps are pinned or justified.
- Verify cache keys cannot leak cross-branch state.
- Require a failure-mode note for pipeline-level changes.
