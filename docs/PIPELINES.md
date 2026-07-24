# Pipelines

Pipelines turn multiple skills into an ordered workflow. Bundled pipelines use
`profile: coordination`: their artifact fields are progress records reported by
the caller, not merge, release, deployment, or security approvals.

## Gate Verification

`must_produce` and `min_length` validate state reported by the caller. For a gate that must
verify a real local result, add a repository-controlled `check_command`:

```yaml
gate:
  must_produce: test_report
  check_command: python -m pytest tests/unit -q
```

The command is parsed without a shell, runs in the server's current working directory with a
constrained environment, and has a 60-second timeout. Treat pipeline YAML as trusted code: do
not allow unreviewed users or remote skill imports to add `check_command`. This is a local
verification hook, not a substitute for CI isolation, deployment approval, or model evaluation.

For a repository-controlled approval workflow, declare `profile: production`.
Production profiles fail to load unless every step configures all of:

- `require_verified_evidence: true`
- a non-empty `allowed_verifiers` list
- a repository-controlled `check_command`

```yaml
id: release-review
name: Release review
profile: production
steps:
  - id: verify
    skill: team-review
    next: []
    gate:
      must_produce: test_report
      require_verified_evidence: true
      allowed_verifiers: [repository-ci]
      max_evidence_age_seconds: 3600
      max_artifact_bytes: 20971520
      check_command: python tools/verify_release.py
```

Strong evidence requires a matching SHA-256 digest, an allowlisted `verified_by`
value, a timezone-aware non-future timestamp within the configured age, and
bounded content. The metadata identifies the expected verifier but is not a
signature by itself; `check_command` is therefore mandatory in a production
profile. Before running that command, the state store atomically claims a
time-limited step lease and exposes a stable
`SKILLS_ORCHESTRATOR_EXECUTION_ID` so the verifier can implement idempotency.
It also exposes `SKILLS_ORCHESTRATOR_EVIDENCE_MANIFEST`, a compact JSON list of
the exact artifact keys, types, digests, and file URIs being checked.
Pipeline authors must still ensure the verifier is side-effect safe.

## Minimal Pipeline

Create `config/pipelines/code-review.yaml`:

```yaml
id: code-review
name: Code Review
profile: coordination
steps:
  - id: inspect
    skill: team-debugging
    next: [test]
    gate:
      must_produce: [root_cause]
      min_length: 50

  - id: test
    skill: team-tdd
    next: [review]
    gate:
      must_produce: [test_code]
      min_length: 100

  - id: review
    skill: team-review
    next: []
    gate:
      must_produce: [review_comments]
```

Run locally:

```bash
skills-orchestrator pipeline list --config config/skills.yaml
skills-orchestrator pipeline start code-review --config config/skills.yaml
```

Pipeline run state is stored under `~/.skills-orchestrator` by default. In CI or shared developer
machines, pin it to the repository workspace so `status`, `resume`, and `advance` never pick up
another repository's latest run:

```bash
skills-orchestrator pipeline start code-review \
  --config config/skills.yaml \
  --state-dir .skills-orchestrator

skills-orchestrator pipeline advance code-review \
  --config config/skills.yaml \
  --state-dir .skills-orchestrator
```

The same default can be set with `SKILLS_ORCHESTRATOR_STATE_DIR=.skills-orchestrator`.

## MCP Runtime

When served through MCP, pipelines expose:

- `pipeline_start`
- `pipeline_status`
- `pipeline_list_runs`
- `pipeline_advance`
- `pipeline_resume`

Pipeline skills must exist in the active registry for the selected zone.

## Gate Guidance

Use gates to require evidence, not to guess quality. Good gate fields are concrete artifacts such
as `root_cause`, `test_code`, `review_comments`, `rollback_plan`, or `release_note`.

`must_produce` can be a single artifact key or a list of keys. When a list is used, every artifact
must exist in the run context before the step can advance.
