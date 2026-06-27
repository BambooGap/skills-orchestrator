# ADR 0001: v3 Commercial Boundary

Status: accepted

Date: 2026-06-21

## Context

Skills Orchestrator is moving from a local skill compiler/checker into an open-source SkillOps
governance layer. The project can support commercial products, but adding hosted SaaS concerns
directly to the OSS core would increase maintenance burden and reduce trust.

## Decision

The OSS core emits portable artifacts and schemas. Hosted products consume those artifacts.

The repository may include:

- CLI commands,
- schemas,
- GitHub Action automation,
- workflow templates,
- docs,
- examples,
- integration scaffolds.

The repository must not include:

- billing,
- tenant databases,
- GitHub App private key handling,
- hosted API servers,
- enterprise dashboards,
- proprietary policy decision engines.

## Consequences

This keeps the open-source project credible and useful on its own. It also leaves a clean commercial
path for hosted registry, GitHub App, dashboard, support, and enterprise policy packs without
locking users into a private format.
