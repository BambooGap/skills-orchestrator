# Authorized Pilot Outreach

Use this guide when a real repository owner is considering a SkillOps pilot. It sits before
[External Pilot Intake](external-pilot-intake.md): outreach gets explicit permission, intake decides
whether the repository is ready, and the [Pilot Evidence Pack](pilot-evidence-pack.md) records the
run.

This document is not an adopter list. Do not cite a repository publicly until its owner explicitly
approves public listing.

## What Authorization Means

Keep the consent level explicit:

| Consent level | What is allowed | What is not allowed |
| --- | --- | --- |
| Private technical pilot | Run SkillOps locally or in the repository's CI and share private artifacts with the repo owner. | No public repository name, logo, quote, or adopter claim. |
| Public pilot mention | Say that a repository is evaluating SkillOps, only if the owner approves that wording. | No success claim, production claim, or case study. |
| Public adopter / case study | Publish repository name, approved quote, and a case study after a validated pilot record. | No runtime control-plane, SLSA certification, or compliance claim beyond the evidence. |

When in doubt, keep `public_listing.status` as `not-requested`.

## Maintainer Request Template

Open an issue, discussion, or email with this text:

```markdown
Hi maintainers,

I would like to run a small SkillOps pilot against this repository to evaluate CI-native governance
for AI instruction artifacts. The pilot would add or test only these surfaces:

- `config/skills.yaml`
- `skills/`
- `.github/workflows/skillops.yml`
- optional generated `AGENTS.md` and `skills.lock.json`

The pilot would not add a runtime service, hosted backend, secret broker, budget enforcer, or agent
execution control plane. It only checks instruction metadata, policy rules, registry diffs, SARIF,
conformance, and evidence artifacts.

Please choose one option:

- [ ] Private technical pilot only. Do not mention this repository publicly.
- [ ] Public pilot mention is allowed, but no adopter or success claim.
- [ ] Public adopter listing / case study may be requested after artifacts pass review.

If approved, I will share:

- check JSON and SARIF
- conformance report
- doctor report
- registry diff
- evidence manifest
- reviewer summary
- external pilot record with `public_listing.status` matching your choice

No public case study, quote, logo, or `ADOPTERS.md` entry will be created without explicit approval.
```

## What To Record

Before running the pilot, record:

- repository URL and exact commit SHA,
- default branch name used by the workflow,
- pilot owner and reviewer contact,
- CI system and artifact retention policy,
- SkillOps version and policy pack,
- requested public listing status.

After running the pilot, record:

- whether `doctor --profile adopter` passed before and after workflow setup,
- whether `schema audit --stability stable` passed,
- whether `conformance run --profile core` passed,
- which artifacts were retained,
- whether the repository owner approved any public reference.

Validate the final record:

```bash
skills-orchestrator schema validate \
  --kind external-pilot-record \
  --input skillops-pilot/pilot-record.json
```

## Public Claim Guardrails

Use this language until public consent is approved:

- "self-run pilot" when the repository owner did not authorize the run,
- "private technical pilot" when the owner approved private evaluation only,
- "authorized public pilot" only when public pilot mention is approved,
- "adopter" only after owner approval and a validated pilot record.

Do not publish:

- repository name for private pilots,
- maintainer quotes without written approval,
- screenshots containing private CI details,
- production success claims without a retained evidence pack,
- runtime security claims from review artifacts.

## Handoff Order

1. Ask for authorization with the template above.
2. Run [External Pilot Intake](external-pilot-intake.md).
3. Run the [Adoption Playbook](adoption-playbook.md) in advisory mode.
4. Archive the [Pilot Evidence Pack](pilot-evidence-pack.md).
5. Validate the external pilot record.
6. Request public listing approval only after artifacts are reviewable.
7. Use the [Pilot Case Study Template](pilot-case-study-template.md) only when approved.
