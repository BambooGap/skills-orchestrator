"""Built-in policy packs for team skill governance."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from skills_orchestrator.diagnostic import Diagnostic
from skills_orchestrator.models import Config, SkillMeta


TEAM_STANDARD_PACK = "builtin/team-standard"
ALLOWED_LIFECYCLES = {"active", "beta", "deprecated", "retired"}


@dataclass(frozen=True)
class PolicyPack:
    """Executable governance policy for skills metadata."""

    pack_id: str
    name: str
    description: str


BUILTIN_POLICY_PACKS: dict[str, PolicyPack] = {
    TEAM_STANDARD_PACK: PolicyPack(
        pack_id=TEAM_STANDARD_PACK,
        name="Team Standard",
        description=(
            "Requires owner, source, version, lifecycle, and approver metadata "
            "needed for team review and commercial auditability."
        ),
    )
}


def normalize_policy_packs(policy_packs: list[str] | tuple[str, ...] | None) -> list[str]:
    """Validate and normalize requested policy pack identifiers."""
    normalized: list[str] = []
    for pack_id in policy_packs or []:
        if pack_id not in BUILTIN_POLICY_PACKS:
            known = ", ".join(sorted(BUILTIN_POLICY_PACKS))
            raise ValueError(f"Unknown policy pack '{pack_id}'. Built-in packs: {known}")
        if pack_id not in normalized:
            normalized.append(pack_id)
    return normalized


def policy_pack_diagnostics(
    cfg: Config, policy_packs: list[str] | tuple[str, ...]
) -> list[Diagnostic]:
    """Run diagnostics contributed by policy packs."""
    normalized = normalize_policy_packs(policy_packs)
    diagnostics: list[Diagnostic] = []
    if TEAM_STANDARD_PACK in normalized:
        diagnostics.extend(_team_standard_diagnostics(cfg))
    return diagnostics


def _team_standard_diagnostics(cfg: Config) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    for skill in cfg.skills:
        path = _skill_path(cfg, skill)
        rel = _relative_path(path, Path(cfg.base_dir))

        if not skill.owner.strip():
            diagnostics.append(
                Diagnostic.from_rule(
                    "SO008",
                    f"Skill '{skill.id}' is missing owner metadata required by {TEAM_STANDARD_PACK}.",
                    file=rel,
                    line=1,
                    skill_id=skill.id,
                    suggested_fix="Add owner: <team-or-person> to the skill frontmatter.",
                    metadata={"policy_pack": TEAM_STANDARD_PACK},
                )
            )

        if not skill.source.strip():
            diagnostics.append(
                Diagnostic.from_rule(
                    "SO009",
                    f"Skill '{skill.id}' is missing source metadata required by {TEAM_STANDARD_PACK}.",
                    file=rel,
                    line=1,
                    skill_id=skill.id,
                    suggested_fix="Add source: <repo|url|internal-doc> to the skill frontmatter.",
                    metadata={"policy_pack": TEAM_STANDARD_PACK},
                )
            )

        if not skill.version.strip():
            diagnostics.append(
                Diagnostic.from_rule(
                    "SO010",
                    f"Skill '{skill.id}' is missing version metadata required by {TEAM_STANDARD_PACK}.",
                    file=rel,
                    line=1,
                    skill_id=skill.id,
                    suggested_fix="Add version: <semver-or-date> to the skill frontmatter.",
                    metadata={"policy_pack": TEAM_STANDARD_PACK},
                )
            )

        if skill.lifecycle not in ALLOWED_LIFECYCLES:
            diagnostics.append(
                Diagnostic.from_rule(
                    "SO011",
                    f"Skill '{skill.id}' lifecycle '{skill.lifecycle}' is not allowed by {TEAM_STANDARD_PACK}.",
                    file=rel,
                    line=1,
                    skill_id=skill.id,
                    suggested_fix=("Use one of: " + ", ".join(sorted(ALLOWED_LIFECYCLES)) + "."),
                    metadata={
                        "policy_pack": TEAM_STANDARD_PACK,
                        "allowed_lifecycles": sorted(ALLOWED_LIFECYCLES),
                    },
                )
            )

        if skill.load_policy == "require" and not skill.approvers:
            diagnostics.append(
                Diagnostic.from_rule(
                    "SO012",
                    f"Required skill '{skill.id}' has no approvers metadata.",
                    file=rel,
                    line=1,
                    skill_id=skill.id,
                    suggested_fix="Add approvers: [<reviewer-or-team>] for forced runtime injection.",
                    metadata={"policy_pack": TEAM_STANDARD_PACK},
                )
            )
    return diagnostics


def _skill_path(cfg: Config, skill: SkillMeta) -> Path:
    path = Path(skill.path)
    if path.is_absolute():
        return path
    return (Path(cfg.base_dir) / path).resolve()


def _relative_path(path: Path, base: Path) -> str:
    try:
        return str(path.resolve().relative_to(base.resolve()))
    except ValueError:
        return str(path)
