# Negative Conformance Fixtures

This directory contains intentionally invalid SkillOps projects. They are designed for platform
teams, security reviewers, and third-party implementers who need to prove that malformed AI
instruction artifacts fail deterministically.

These fixtures are different from the normal pilot examples:

- they are supposed to emit the expected `check` rule ids,
- each case documents the expected SkillOps rule ids,
- the cases are safe to copy into CI tests for downstream integrations,
- they are not adopter examples and must not be listed as production usage.

Some cases produce warnings instead of errors. In text or JSON mode, those cases may exit `0`
unless `--fail-on warning` is set. For negative conformance, the contract is that the expected rule
ids appear with stable locations, severities, and fixes; use `--fail-on warning` when a shell-level
failure is required.

## Run All Cases

```bash
python -m pytest tests/test_negative_conformance_examples.py
```

## Run A Single Case Manually

```bash
skills-orchestrator check \
  --config examples/negative-conformance/cases/external-trust/config/skills.yaml \
  --policy-pack builtin/engineering-grade \
  --fail-on warning \
  --format json
```

## Case Index

The machine-readable index is `cases.json`.

| Case | Policy packs | Expected rules |
| --- | --- | --- |
| `missing-governance` | `builtin/team-standard` | `SO008`, `SO009`, `SO010` |
| `invalid-load-policy` | none | `SO013` |
| `invalid-lifecycle-required-approvers` | `builtin/team-standard` | `SO011`, `SO012` |
| `invalid-review-window` | `builtin/engineering-grade` | `SO015` |
| `expired-review-window` | `builtin/engineering-grade` | `SO016` |
| `external-trust` | `builtin/engineering-grade` | `SO019`, `SO020` |
| `duplicate-id` | none | `SO002` |

## Why This Matters

Positive examples prove that a happy path can pass. Negative fixtures prove that the contract is a
real gate. For enterprise pilots, both are required: the tool must accept good instruction assets
and reject high-risk instruction assets with stable rule ids, locations, severities, and fixes.
