# Woodpecker Pilot

This pilot models a CI system where pipeline definitions, runner trust, and
plugin releases need governance before merge.

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
