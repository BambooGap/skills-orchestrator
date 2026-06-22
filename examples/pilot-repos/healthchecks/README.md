# Healthchecks Pilot

This pilot models a monitoring / alerting repository where runbook skills and
release skills need ownership, review windows, and CI visibility.

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

The workflow in `.github/workflows/skillops.yml` runs the same gate, uploads SARIF,
and can post a registry diff comment on pull requests.
