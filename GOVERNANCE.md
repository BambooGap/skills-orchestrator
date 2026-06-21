# Governance

Skills Orchestrator is currently an early-stage, single-maintainer open-source project.

## Current Model

- Maintainer decisions are made in public issues and pull requests when possible.
- The maintainer may merge small fixes directly after CI passes.
- Larger behavior, schema, or contract changes should be discussed in an issue or PR before merge.
- There is no Technical Steering Committee, foundation home, or formal voting process today.

## Contract Changes

Changes to `SPEC.md`, JSON Schemas, action inputs, CLI output formats, or evidence artifact formats
should explain compatibility impact in the PR description.

Breaking changes should create a new schema or contract version rather than silently changing a v1
contract.

## Future Governance

If the project gains multiple active maintainers or external adopters, this document should be
updated before claiming foundation readiness or multi-organization governance.
