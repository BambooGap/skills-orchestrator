# External Adoption Record Example

This reference example shows how a repository can record an external SkillOps adoption without claiming public
adoption too early.

It is intentionally generic. Do not copy it into `ADOPTERS.md`; use it as the shape for a real
adoption handoff after a repository runs SkillOps in its own CI.

## Validate

```bash
skills-orchestrator schema validate \
  --kind external-adoption-record \
  --input examples/external-adoption-record/advisory-adoption-record.json
```

## What It Proves

- The adoption has an owner, CI system, SkillOps version, policy pack, and gate mode.
- Maintainer authorization is explicit and separate from public listing.
- Required evidence artifacts are marked present, missing, or not applicable.
- Promotion decisions are explicit and time-stamped.
- Public adopter listing consent is separate from technical success.

## Boundary

An external adoption record is review evidence. It does not prove that a repository is a public adopter,
that an organization approved a testimonial, or that SkillOps became a runtime control plane. Keep
`authorization.tier` conservative until a maintainer explicitly approves public reference.
