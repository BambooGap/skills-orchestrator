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
bounded files. Production profiles reject inline evidence: each artifact must
use a `file://` URI beneath the configured artifact root. Parent directories
and the final file are opened without following symlinks.

Production execution also requires a writable audit directory. MCP servers use
`--audit-dir`; CLI runs use `SKILLS_ORCHESTRATOR_AUDIT_DIR`. The audit log is
strict for production runs: failure to append the run or step event prevents
the state transition from becoming approved. Before a `gate_passed` event is
written, the candidate state and a stable approval outbox record are saved.
If the state save fails, no passing event is emitted. If the audit write fails,
the persisted run materializes as `pending_audit`; retrying the advance flushes
the same idempotent event without rerunning the verifier. Recovery requires the
same canonical audit directory and the exact stable event payload; a changed
sink fails with `PRODUCTION_AUDIT_SINK_MISMATCH`. Successful writes clear the
approval outbox immediately. Events include
pipeline, run, step, execution, evidence digest, and verifier identifiers in a
sequenced hash chain.

Strict writes validate the complete chain from sequence 1 through the current
tail, including every event hash, sequence continuity, and each
`previous_event_hash` link. Rotate a legacy unchained log before enabling a
production profile.

Before running `check_command`, the shared execution service atomically claims
a time-limited step lease. The verifier receives:

- `SKILLS_ORCHESTRATOR_EXECUTION_ID`
- `SKILLS_ORCHESTRATOR_PIPELINE_ID`
- `SKILLS_ORCHESTRATOR_RUN_ID`
- `SKILLS_ORCHESTRATOR_STEP_ID`
- `SKILLS_ORCHESTRATOR_EVIDENCE_DIGEST`
- `SKILLS_ORCHESTRATOR_VERIFIER`
- `SKILLS_ORCHESTRATOR_EVIDENCE_MANIFEST`

The command must emit one UTF-8 JSON object, no larger than 64 KiB, with
`ok: true` and all six binding fields exactly matching the environment. A
successful exit code without that attestation is a failed production gate.
This binds the verifier result to the exact lease and evidence set; it does not
turn an untrusted verifier script into a trusted identity. Repository owners
must review the verifier and use signed CI/OIDC attestations for higher-risk
approval.

Generate evidence URIs with the canonical artifact root, especially on macOS
where `/var` may resolve to `/private/var`:

```python
from skills_orchestrator.pipeline import build_evidence_uri

uri = build_evidence_uri("reports/test.json", artifact_root=".")
```

The helper resolves both paths, rejects files outside the root, and returns the
canonical `file://` URI expected by the no-symlink file opener.

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
