# Reference Repository Examples

These examples are copyable SkillOps starter packs for real repository shapes.
They are not forks of the upstream projects. Each directory models the minimum
files a platform team would add to a repository during an adoption.

| Adoption | Target shape | What it proves |
| --- | --- | --- |
| `healthchecks` | Monitoring / ops application | Operational skills can be owned, reviewed, and gated in CI. |
| `umami` | Analytics application | Privacy and migration skills can be reviewed as instruction assets. |
| `woodpecker` | CI system | Pipeline and runner-safety skills can be checked before PR merge. |

## Run One Adoption

From any adoption directory:

```bash
python3.12 -m pip install skills-orchestrator

skills-orchestrator check \
  --config config/skills.yaml \
  --policy-pack builtin/team-standard \
  --fail-on warning

skills-orchestrator build --lock
skills-orchestrator doctor --profile adopter
skills-orchestrator conformance run --profile core

mkdir -p evidence
skills-orchestrator evidence export \
  --config config/skills.yaml \
  --out evidence

skills-orchestrator dashboard snapshot \
  --evidence-dir evidence \
  --output evidence/dashboard-snapshot.json
```

To test PR review output:

```bash
skills-orchestrator registry build \
  --config-glob config/skills.yaml \
  --output evidence/registry-before.json

# edit one skill version or owner here

skills-orchestrator registry build \
  --config-glob config/skills.yaml \
  --output evidence/registry-after.json

skills-orchestrator registry diff \
  evidence/registry-before.json \
  evidence/registry-after.json \
  --format markdown \
  --output evidence/registry-diff.md \
  --force

skills-orchestrator registry comment-body \
  evidence/registry-diff.md \
  --output evidence/registry-diff-comment.md
```
