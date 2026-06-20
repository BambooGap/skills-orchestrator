# Zones

Zones decide which skills are visible for a repository area or operating mode.

## Minimal Zone

```yaml
zones:
  - id: default
    name: Default
    load_policy: free
    rules: []
```

## Path-Matched Zones

```yaml
zones:
  - id: frontend
    name: Frontend
    load_policy: require
    priority: 100
    rules:
      - pattern: "src/frontend/**"

  - id: backend
    name: Backend
    load_policy: require
    priority: 100
    rules:
      - pattern: "src/backend/**"

  - id: default
    name: Default
    load_policy: free
    rules: []
```

`load_policy: require` upgrades visible free skills to required for that zone. Use it for small,
high-confidence rule sets only.

## Exclusive Zones

```yaml
zones:
  - id: incident
    name: Incident Response
    load_policy: exclusive
    skills: [incident-triage, rollback-plan]
    allow_base_skills: [git-operations]
    rules:
      - pattern: "incidents/**"
```

Exclusive zones limit visible skills to the listed skills plus `allow_base_skills`.

## Selection Rules

- `build` and `sync` can auto-detect zones from the current working directory.
- `check`, `manifest`, and `policy export` use the default zone unless `--zone` is provided.
- The default zone is the zone with `id: default`, or the first zone without rules.
