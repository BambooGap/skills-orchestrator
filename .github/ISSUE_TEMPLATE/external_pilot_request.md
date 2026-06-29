---
name: External Pilot Request
about: Request or authorize a SkillOps pilot for an external repository
title: '[Pilot] '
labels: adoption,pilot
assignees: ''
---

## Repository

- Repository URL:
- Default branch:
- CI system:
- Pilot owner:

## Requested Pilot Scope

- [ ] Not interested. Please close this request and do not follow up.
- [ ] Private technical pilot only. Do not mention this repository publicly.
- [ ] Public pilot mention is allowed, but no adopter or success claim.
- [ ] Public adopter listing / case study may be requested after artifacts pass review.

## Expected SkillOps Surfaces

- [ ] `config/skills.yaml`
- [ ] `skills/`
- [ ] `.github/workflows/skillops.yml`
- [ ] optional `AGENTS.md`
- [ ] optional `skills.lock.json`
- [ ] CI artifacts for check JSON, SARIF, conformance, registry diff, and evidence manifest

## Boundaries

- [ ] This pilot is CI governance for AI instruction artifacts.
- [ ] No PR will be opened against this repository unless maintainers ask for one.
- [ ] No private data, secrets, proprietary CI logs, or non-public artifacts will be requested.
- [ ] This pilot is not an agent runtime control plane.
- [ ] This pilot is not tenant isolation, budget enforcement, secret isolation, or worker sandboxing.
- [ ] No public case study, quote, logo, or adopter listing is approved unless stated explicitly.

If maintainers close this issue or reply "not interested", the requester should stop follow-up and
must not cite this repository publicly.

## Notes

Add any retention requirements, security review constraints, or reviewer contacts here.
