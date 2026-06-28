# External Pilot Record Example

This fixture shows how a repository can record an external SkillOps pilot without claiming public
adoption too early.

It is intentionally synthetic. Do not copy it into `ADOPTERS.md`; use it as the shape for a real
pilot handoff after a repository runs SkillOps in its own CI.

## Validate

```bash
skills-orchestrator schema validate \
  --kind external-pilot-record \
  --input examples/external-pilot-record/advisory-pilot-record.json
```

## What It Proves

- The pilot has an owner, CI system, SkillOps version, policy pack, and gate mode.
- Required evidence artifacts are marked present, missing, or not applicable.
- Promotion decisions are explicit and time-stamped.
- Public adopter listing consent is separate from technical success.

## Boundary

An external pilot record is review evidence. It does not prove that a repository is a public adopter,
that an organization approved a testimonial, or that SkillOps became a runtime control plane.
