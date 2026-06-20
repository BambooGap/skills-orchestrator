"""Static catalog of adjacent agent-tooling integrations.

The catalog is intentionally dependency-free. It names ecosystem positions and
recommended integration strategy so teams can route skills-orchestrator outputs
into their own harnesses, memory systems, graph tools, and CI without this
package becoming a wrapper around every fast-moving agent project.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class Integration:
    """Adjacent project or surface that can consume SkillOps evidence."""

    id: str
    name: str
    layer: str
    relationship: str
    strategy: str
    url: str
    commercial_value: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


INTEGRATIONS: tuple[Integration, ...] = (
    Integration(
        id="superpowers",
        name="Superpowers",
        layer="methodology-control",
        relationship="upstream-methodology",
        strategy="Export skills, policy reports, and team contracts; do not reimplement workflow skills.",
        url="https://github.com/obra/Superpowers",
        commercial_value="Gives teams a disciplined development method while skills-orchestrator supplies governance evidence.",
    ),
    Integration(
        id="codegraph",
        name="CodeGraph",
        layer="code-structure-memory",
        relationship="upstream-context-index",
        strategy="Use as code retrieval/indexing; attach skill manifests and audit records as external context.",
        url="https://github.com/colbymchenry/codegraph",
        commercial_value="Reduces repeated code exploration cost while this tool governs instruction assets.",
    ),
    Integration(
        id="supermemory-service",
        name="supermemory-service",
        layer="business-memory",
        relationship="local-business-memory",
        strategy="Store registry manifests, policy decisions, and release evidence; keep memory semantics outside this package.",
        url="project:supermemory-service",
        commercial_value="Turns skill governance outputs into durable business memory and connector history.",
    ),
    Integration(
        id="codex-claude-code",
        name="Codex / Claude Code",
        layer="execution-model",
        relationship="runtime-consumer",
        strategy="Serve MCP prepare_context decisions and AGENTS.md exports; keep execution in the harness.",
        url="https://github.com/openai/codex",
        commercial_value="Lets existing coding agents consume one governed skill contract instead of per-agent prompt drift.",
    ),
    Integration(
        id="ci-test-typecheck",
        name="CI / test / typecheck",
        layer="verification",
        relationship="required-gate",
        strategy="Upload SARIF, JSON check reports, manifests, policy exports, registry output, and doctor results.",
        url="https://docs.github.com/actions",
        commercial_value="Makes instruction governance enforceable before merge, not advisory after incidents.",
    ),
    Integration(
        id="understand-anything",
        name="Understand Anything",
        layer="post-hoc-understanding",
        relationship="visualization-consumer",
        strategy="Visualize project/code/docs; treat skills-orchestrator registry as an input artifact, not a runtime dependency.",
        url="https://github.com/Egonex-AI/Understand-Anything",
        commercial_value="Improves onboarding and review of the governed skill system.",
    ),
    Integration(
        id="omnigent",
        name="Omnigent",
        layer="multi-agent-orchestration",
        relationship="meta-harness-consumer",
        strategy="Feed policy decisions, audit records, and registry manifests into the meta-harness policy layer.",
        url="https://github.com/omnigent-ai/omnigent",
        commercial_value="Lets multi-agent orchestration reuse the same skill policies across harnesses.",
    ),
    Integration(
        id="graphiti",
        name="Graphiti / Zep",
        layer="temporal-context-graph",
        relationship="memory-backend-candidate",
        strategy="Optional downstream storage for evolving skill ownership, incidents, and policy evidence.",
        url="https://github.com/getzep/graphiti",
        commercial_value="Adds temporal provenance when teams need governed memory beyond flat JSON artifacts.",
    ),
)


def get_integrations(layer: str | None = None) -> list[Integration]:
    """Return catalog entries, optionally filtered by ecosystem layer."""
    if layer is None:
        return list(INTEGRATIONS)
    return [integration for integration in INTEGRATIONS if integration.layer == layer]
