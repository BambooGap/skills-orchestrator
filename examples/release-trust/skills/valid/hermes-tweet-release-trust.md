---
id: hermes-tweet-release-trust
name: Hermes Tweet Release Trust
summary: Real external skill fixture for a MIT-licensed Hermes Agent X/Twitter plugin.
tags: [external, provenance, release-trust, hermes-agent, twitter]
load_policy: free
priority: 70
zones: [default]
conflict_with: []
owner: platform-team
source: https://raw.githubusercontent.com/Xquik-dev/hermes-tweet/87ca73c0e3de48ce209d07754c0e148f9b9feab2/hermes_tweet/skills/hermes-tweet/skill-card.md
version: 0.1.6
lifecycle: active
approvers: [platform-team]
reviewed_at: 2026-06-29
expires_at: 2026-12-29
license: MIT
provenance:
  source_url: https://raw.githubusercontent.com/Xquik-dev/hermes-tweet/87ca73c0e3de48ce209d07754c0e148f9b9feab2/hermes_tweet/skills/hermes-tweet/skill-card.md
  source_ref: 87ca73c0e3de48ce209d07754c0e148f9b9feab2
  source_commit: 87ca73c0e3de48ce209d07754c0e148f9b9feab2
  content_hash: sha256:872f98d1c9ba796e252ea7a3e0f76565c518e4c29b533baaad24d228de9ed5bd
  fetched_at: 2026-06-29T04:22:28Z
---
# Hermes Tweet Release Trust

Use this fixture when testing external SkillOps provenance for a real public
agent plugin. Hermes Tweet is a native Hermes Agent plugin for X/Twitter
automation through Xquik. It ships read-first workflows and keeps account
changing actions behind explicit runtime approval.

This fixture is not a default install recommendation. It exists to prove that a
MIT-licensed external agent skill can carry source URL, resolved commit, content
hash, review-window, approver, and license metadata under the engineering-grade
policy pack.

Reviewers should verify the pinned source before promoting this skill:

1. Confirm the raw source URL resolves to the pinned commit.
2. Confirm the repository license is MIT.
3. Confirm the source hash matches the recorded SHA-256 value.
4. Confirm the review window is still current.

Runtime use remains opt-in. A Hermes Agent user still needs to install Hermes
Tweet from its source repository, configure `XQUIK_API_KEY` in the runtime
environment, and leave write-capable actions disabled unless a task explicitly
requires them.
