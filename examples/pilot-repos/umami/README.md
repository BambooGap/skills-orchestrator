# Umami Pilot

This pilot models an analytics repository where privacy, schema migration, and
release-observability skills need explicit review.

## Local Gate

```bash
skills-orchestrator check \
  --config config/skills.yaml \
  --policy-pack builtin/team-standard \
  --fail-on warning

skills-orchestrator build --lock
skills-orchestrator doctor --profile adopter
skills-orchestrator conformance run --profile core
```

## Evidence

```bash
mkdir -p evidence
skills-orchestrator evidence export \
  --config config/skills.yaml \
  --out evidence
```
