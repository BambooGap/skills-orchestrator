# Pipelines

Pipelines turn multiple skills into a gated workflow.

## Minimal Pipeline

Create `config/pipelines/code-review.yaml`:

```yaml
id: code-review
name: Code Review
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
