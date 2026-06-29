# Adoption Authorization

Use this guide when a real repository owner is considering a SkillOps adoption. It sits before
[External Adoption Intake](external-adoption-intake.md): outreach gets explicit permission, intake decides
whether the repository is ready, and the [Adoption Evidence Pack](adoption-evidence-pack.md) records the
run.

This document is not an adopter list. Do not cite a repository publicly until its owner explicitly
approves public listing.

## What Authorization Means

Keep the consent level explicit:

| Consent level | What is allowed | What is not allowed |
| --- | --- | --- |
| Not requested / pending | Prepare a proposed adoption privately and wait for maintainer response. | No public repository name, PR, follow-up campaign, or adopter claim. |
| Declined / no follow-up | Stop the adoption request and do not contact again on the same thread. | No public mention, no case study, no "declined" naming, no repeated follow-up. |
| Private technical adoption | Run SkillOps locally or in the repository's CI and share private artifacts with the repo owner. | No public repository name, logo, quote, or adopter claim. |
| Public reference mention | Say that a repository is evaluating SkillOps, only if the owner approves that wording. | No success claim, production claim, or case study. |
| Public adopter / case study | Publish repository name, approved quote, and a case study after a validated adoption record. | No runtime control-plane, SLSA certification, or compliance claim beyond the evidence. |

When in doubt, keep `public_listing.status` as `not-requested`.

## Maintainer Request Template

Open an issue, discussion, or email with this text:

```markdown
Hi maintainers,

I would like to run SkillOps CI governance against this repository for AI instruction artifacts. The
adoption would add only these surfaces:

- `config/skills.yaml`
- `skills/`
- `.github/workflows/skillops.yml`
- optional generated `AGENTS.md` and `skills.lock.json`

The adoption would not add a runtime service, hosted backend, secret broker, budget enforcer, or agent
execution control plane. It only checks instruction metadata, policy rules, registry diffs, SARIF,
conformance, and evidence artifacts.

Please choose one option:

- [ ] Not interested. Please close this request and do not follow up.
- [ ] Private technical adoption only. Do not mention this repository publicly.
- [ ] Public reference mention is allowed, but no adopter or success claim.
- [ ] Public adopter listing / case study may be requested after artifacts pass review.

If approved, I will share:

- check JSON and SARIF
- conformance report
- doctor report
- registry diff
- evidence manifest
- reviewer summary
- external adoption record with `public_listing.status` matching your choice

No public case study, quote, logo, or `ADOPTERS.md` entry will be created without explicit approval.
If you close this request or reply "not interested", I will not follow up and will not cite this
repository publicly.
```

## What To Record

Before running the adoption, record:

- repository URL and exact commit SHA,
- default branch name used by the workflow,
- adoption owner and reviewer contact,
- CI system and artifact retention policy,
- SkillOps version and policy pack,
- authorization tier and decision timestamp,
- requested public listing status.

After running the adoption, record:

- whether `doctor --profile adopter` passed before and after workflow setup,
- whether `schema audit --stability stable` passed,
- whether `conformance run --profile core` passed,
- which artifacts were retained,
- whether the repository owner approved any public reference.

Validate the final record:

```bash
skills-orchestrator schema validate \
  --kind external-adoption-record \
  --input skillops-adoption/adoption-record.json
```

## Public Claim Guardrails

Use this language until public consent is approved:

- "self-run adoption" when the repository owner did not authorize the run,
- "declined-no-follow-up" when the maintainer declines or closes the request,
- "private technical adoption" when the owner approved private evaluation only,
- "authorized public adoption" only when public reference mention is approved,
- "adopter" only after `public_listing.status` is approved, `authorization.tier` is
  `public-adopter-reference` or `public-case-study`, and the adoption record validates.

Do not publish:

- repository name for private adoptions,
- repository name for declined or no-response requests,
- maintainer quotes without written approval,
- screenshots containing private CI details,
- production success claims without a retained evidence pack,
- runtime security claims from review artifacts.

## Handoff Order

1. Ask for authorization with the template above.
2. Run [External Adoption Intake](external-adoption-intake.md).
3. Run the [Adoption Playbook](adoption-playbook.md) in advisory mode.
4. Archive the [Adoption Evidence Pack](adoption-evidence-pack.md).
5. Validate the external adoption record.
6. Request public listing approval only after artifacts are reviewable.
7. Use the [Adoption Case Study Template](adoption-case-study-template.md) only when approved.
