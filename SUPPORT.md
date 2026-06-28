# Support

Skills Orchestrator is an open-source project. Support is best-effort unless a separate commercial
agreement exists outside the OSS repository.

## Where To Ask

- Bugs: open a GitHub issue with a minimal reproduction, CLI version, Python version, operating
  system, and the exact command output.
- Usage questions: open a GitHub issue using the question template.
- Security reports: follow `SECURITY.md`; do not post exploit details in public issues.
- Production adoption: start with `docs/production-adoption.md` and include which gate you are
  evaluating: advisory, warning gate, engineering-grade gate, or release gate.

## Supported Versions

Security and compatibility fixes target the latest released minor line. Older tags remain available
for audit and rollback, but this project does not currently maintain multiple long-term support
branches.

## Response Expectations

This is currently a single-maintainer project. Response times may vary. High-quality reports with
reproducible commands, small fixtures, and clear expected behavior are more likely to be handled
quickly.

## Scope Boundaries

The OSS core supports CI governance for AI instruction artifacts. It does not provide hosted
multi-tenant service operations, runtime tenant isolation, budget enforcement, secret brokering, or
agent worker sandbox support.
