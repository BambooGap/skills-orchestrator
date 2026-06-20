# Enterprise Narrative

Skills Orchestrator is SkillOps infrastructure for agent instructions.

It treats Markdown skills as governed instruction assets: source-controlled, checked in CI, locked
for reproducibility, exported as machine-readable inventory, and routed at runtime through MCP.

## Buyer And Operator

| Persona | Concern | Product Surface |
| --- | --- | --- |
| Platform engineering | Many teams use inconsistent agent rules. | `check`, zones, GitHub Action, team docs. |
| Security / compliance | Agent instructions are invisible to supply-chain review. | SARIF, manifest, CycloneDX, policy export. |
| Developer experience | Agents need the right skill without bloating context. | MCP `prepare_context`, `search_skills`, `get_skill`. |
| Release engineering | Releases need repeatable evidence. | lock files, release verification, attestations. |

## Ecosystem Routing

- AAIF / agent instruction formats: natural home for instruction packaging and runtime contracts.
- OpenSSF: security story through SARIF, manifests, provenance, pinned Actions, and future SBOM work.
- CNCF: enterprise adoption path through CI/CD, containers, MCP runtime operations, and platform teams.
- SPDX / CycloneDX / GUAC: downstream consumers for instruction inventory once schemas mature.
- OPA: policy-as-code proof surface, not the default runtime decision engine.

## Core Claims

- It is a governance layer for skills, not a model wrapper.
- Resolver decisions remain the source of truth.
- `check` is the adoption lane.
- `manifest` and `policy export` are proof surfaces.
- MCP is the runtime loading lane.
- Docker and GitHub Action reduce integration friction.

## Non-Goals

- Replacing MCP.
- Becoming a general-purpose LLM orchestration framework.
- Running a second policy engine by default.
- Solving prompt injection inside every downstream agent.
- Guaranteeing that a model will obey instructions already present in old conversation context.

## Product Ceiling

The next ceiling is not more CLI commands. The ceiling is becoming the standard control plane for
team-owned agent instruction assets:

1. enforceable policy packs,
2. structured runtime decision records,
3. audit and usage reports,
4. schema-stable manifests,
5. signed release and container evidence,
6. org-level registries for many repositories.
