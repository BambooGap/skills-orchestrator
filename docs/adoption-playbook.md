# Adoption Playbook

This playbook is the shortest path for adopting Skills Orchestrator in a real
repository. It is written for platform teams that want a low-risk pilot before
turning SkillOps checks into a blocking release gate.

For repositories outside this project, first use [External Pilot Intake](external-pilot-intake.md)
to confirm ownership, artifact retention, gate mode, and stop conditions.

## Adoption Modes

| Mode | Gate | Recommended for | Commands |
| --- | --- | --- | --- |
| Advisory | Fails only on errors | First week in a new repo | `check --policy-pack builtin/team-standard` |
| Warning gate | Fails on warnings | Repos with committed skill owners | `check --policy-pack builtin/team-standard --fail-on warning` |
| Engineering gate | Requires trust metadata | Platform-owned production repos | `check --policy-pack builtin/engineering-grade --fail-on warning` |

Start with advisory mode unless the repository already has owners, versions,
sources, lifecycle metadata, and review windows for each skill.

## 15-Minute Pilot

1. Install the CLI:

   ```bash
   python3.12 -m pip install skills-orchestrator
   ```

2. Create a starter kit:

   ```bash
   skills-orchestrator init --template team-standard
   ```

   For repositories that require pinned third-party GitHub Actions, generate the
   stricter starter workflow instead:

   ```bash
   skills-orchestrator init --template team-standard --hardened-workflow
   ```

3. Run the first local gate:

   ```bash
   skills-orchestrator check \
     --config config/skills.yaml \
     --policy-pack builtin/team-standard
   ```

4. Generate reproducibility evidence:

   ```bash
   skills-orchestrator build --lock
   skills-orchestrator doctor --profile adopter
   skills-orchestrator conformance run --profile core
   ```

5. Export the evidence bundle:

   ```bash
   mkdir -p evidence
   skills-orchestrator evidence export \
     --config config/skills.yaml \
     --out evidence

   skills-orchestrator dashboard snapshot \
     --evidence-dir evidence \
     --output evidence/dashboard-snapshot.json
   ```

6. Add the GitHub Action in advisory mode:

   ```yaml
   name: SkillOps

   on:
     pull_request:
     push:
       branches: [main]

   permissions:
     contents: read
     security-events: write
     pull-requests: write

   jobs:
     skillops:
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v4
           with:
             fetch-depth: 0
         - uses: BambooGap/skills-orchestrator@v4.8.28
           with:
             config: config/skills.yaml
             policy-pack: builtin/team-standard
             upload-sarif: true
             registry-diff: true
             reviewer-summary: true
             dashboard-snapshot: true
             comment-registry-diff: true
   ```

   Strict supply-chain environments can replace the checkout line with the
   pinned value emitted by `init --template team-standard --hardened-workflow`.

## Promotion Criteria

Move from advisory to warning gate when all of these are true:

- `doctor --profile adopter` reports `100/100`.
- `conformance run --profile core` reports `14/14 pass`.
- `check --policy-pack builtin/team-standard --fail-on warning` has no findings.
- The repository has committed `skills.lock.json` and generated `AGENTS.md`.
- PR reviewers understand the registry diff comment format.

Move from warning gate to engineering gate when all of these are true:

- Every skill has `owner`, `source`, `version`, `lifecycle`, and `license`.
- External skills have import provenance with commit and content hash evidence.
- Review-window metadata is present and current.
- `builtin/engineering-grade` has no warnings.
- Security reviewers agree that SARIF findings can block merges.

## Pilot Examples

The examples under `examples/pilot-repos/` are copyable starter packs for
real-world repository shapes:

- `healthchecks`: operational runbook and release-check skills for a monitoring app.
- `umami`: privacy, schema migration, and analytics release skills.
- `woodpecker`: CI pipeline, runner security, and plugin release skills.

Each pilot includes:

- `config/skills.yaml`
- sample `skills/*.md`
- `.github/workflows/skillops.yml`
- `evidence/.gitkeep`
- a local reproduction README

## Operating Notes

- Treat `doctor --profile adopter` as the default repo-health gate for new users.
- Use `doctor --profile enterprise` only when the repo already exports evidence bundles.
- Keep `pull_request_target` out of untrusted fork workflows unless the action is pinned and the
  threat model has been reviewed.
- Do not create an `ADOPTERS.md` entry until a real external repo is using the tool.
