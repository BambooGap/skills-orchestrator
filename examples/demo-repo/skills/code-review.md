---
id: code-review
name: Code Review
summary: Review code and skill changes with explicit evidence requirements.
tags: [review, ci, skillops]
load_policy: free
priority: 80
zones: [default]
conflict_with: []
owner: platform-team
source: repo://examples/demo-repo/skills/code-review.md
version: 1.0.0
lifecycle: active
---
# Code Review

Use this skill when reviewing pull requests that change application code or SkillOps metadata.

## Checklist

- Confirm the changed files are in scope for the pull request.
- Run the repository checks or inspect CI results.
- Review generated SARIF, registry diff, and evidence bundle artifacts when present.
- Ask for a smaller change if the pull request mixes unrelated concerns.

## Output

Summarize findings by severity, then list the exact evidence reviewed.
