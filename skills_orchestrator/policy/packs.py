"""Built-in policy packs for team skill governance."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
import re
from urllib.parse import urlparse

from skills_orchestrator.diagnostic import Diagnostic
from skills_orchestrator.models import Config, SkillMeta
from skills_orchestrator.policy.declarative import (
    declarative_policy_pack_diagnostics,
    load_declarative_policy_pack,
)


TEAM_STANDARD_PACK = "builtin/team-standard"
ENGINEERING_GRADE_PACK = "builtin/engineering-grade"
ALLOWED_LIFECYCLES = {"active", "beta", "deprecated", "retired"}
ENGINEERING_GRADE_ALLOWED_LICENSES = {"Apache-2.0", "MIT"}
REQUIRED_PROVENANCE_FIELDS = {
    "source_url",
    "source_ref",
    "source_commit",
    "content_hash",
    "fetched_at",
}


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
    ),
    ENGINEERING_GRADE_PACK: PolicyPack(
        pack_id=ENGINEERING_GRADE_PACK,
        name="Engineering Grade",
        description=(
            "Includes team-standard governance and requires review-window, license, "
            "and external import provenance metadata for enterprise SkillOps change control."
        ),
    ),
}


def normalize_policy_packs(policy_packs: list[str] | tuple[str, ...] | None) -> list[str]:
    """Validate and normalize requested policy pack identifiers."""
    normalized: list[str] = []
    for pack_id in policy_packs or []:
        if pack_id not in BUILTIN_POLICY_PACKS:
            path = Path(pack_id).expanduser()
            if not path.exists():
                known = ", ".join(sorted(BUILTIN_POLICY_PACKS))
                raise ValueError(
                    f"Unknown policy pack '{pack_id}'. Built-in packs: {known}. "
                    "Or pass a local declarative policy pack YAML/JSON file."
                )
            load_declarative_policy_pack(pack_id)
        if pack_id not in normalized:
            normalized.append(pack_id)
    return normalized


def policy_pack_diagnostics(
    cfg: Config, policy_packs: list[str] | tuple[str, ...]
) -> list[Diagnostic]:
    """Run diagnostics contributed by policy packs."""
    normalized = normalize_policy_packs(policy_packs)
    diagnostics: list[Diagnostic] = []
    if TEAM_STANDARD_PACK in normalized or ENGINEERING_GRADE_PACK in normalized:
        diagnostics.extend(_team_standard_diagnostics(cfg))
    if ENGINEERING_GRADE_PACK in normalized:
        diagnostics.extend(_engineering_grade_diagnostics(cfg))
    for pack_id in normalized:
        if pack_id in BUILTIN_POLICY_PACKS:
            continue
        pack = load_declarative_policy_pack(pack_id)
        diagnostics.extend(declarative_policy_pack_diagnostics(cfg, pack))
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


def _engineering_grade_diagnostics(cfg: Config) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []
    today = date.today()
    for skill in cfg.skills:
        path = _skill_path(cfg, skill)
        rel = _relative_path(path, Path(cfg.base_dir))

        normalized_license = _normalize_license_id(skill.license)
        if not skill.license.strip():
            diagnostics.append(
                Diagnostic.from_rule(
                    "SO018",
                    f"Skill '{skill.id}' is missing license metadata required by {ENGINEERING_GRADE_PACK}.",
                    file=rel,
                    line=1,
                    skill_id=skill.id,
                    suggested_fix="Add license: MIT or license: Apache-2.0 to the skill frontmatter.",
                    metadata={
                        "policy_pack": ENGINEERING_GRADE_PACK,
                        "allowed_licenses": sorted(ENGINEERING_GRADE_ALLOWED_LICENSES),
                    },
                )
            )
        elif normalized_license not in ENGINEERING_GRADE_ALLOWED_LICENSES:
            diagnostics.append(
                Diagnostic.from_rule(
                    "SO019",
                    f"Skill '{skill.id}' license '{skill.license}' is not allowed by {ENGINEERING_GRADE_PACK}.",
                    file=rel,
                    line=1,
                    skill_id=skill.id,
                    suggested_fix=(
                        "Use one of: " + ", ".join(sorted(ENGINEERING_GRADE_ALLOWED_LICENSES)) + "."
                    ),
                    metadata={
                        "policy_pack": ENGINEERING_GRADE_PACK,
                        "allowed_licenses": sorted(ENGINEERING_GRADE_ALLOWED_LICENSES),
                        "license": skill.license,
                        "normalized_license": normalized_license,
                    },
                )
            )

        if _is_external_source(skill.source):
            missing_provenance = sorted(
                field
                for field in REQUIRED_PROVENANCE_FIELDS
                if not str(skill.provenance.get(field, "")).strip()
            )
            if missing_provenance:
                diagnostics.append(
                    Diagnostic.from_rule(
                        "SO020",
                        f"Externally sourced skill '{skill.id}' is missing import provenance: {', '.join(missing_provenance)}.",
                        file=rel,
                        line=1,
                        skill_id=skill.id,
                        suggested_fix=(
                            "Record provenance.source_url, source_ref, source_commit, "
                            "content_hash, and fetched_at for imported external skills."
                        ),
                        metadata={
                            "policy_pack": ENGINEERING_GRADE_PACK,
                            "missing_fields": missing_provenance,
                            "source": skill.source,
                        },
                    )
                )

        if not skill.reviewed_at.strip() or not skill.expires_at.strip():
            missing = [
                field
                for field, value in (
                    ("reviewed_at", skill.reviewed_at),
                    ("expires_at", skill.expires_at),
                )
                if not value.strip()
            ]
            diagnostics.append(
                Diagnostic.from_rule(
                    "SO014",
                    f"Skill '{skill.id}' is missing review-window metadata required by {ENGINEERING_GRADE_PACK}: {', '.join(missing)}.",
                    file=rel,
                    line=1,
                    skill_id=skill.id,
                    suggested_fix="Add reviewed_at: YYYY-MM-DD and expires_at: YYYY-MM-DD to the skill frontmatter.",
                    metadata={
                        "policy_pack": ENGINEERING_GRADE_PACK,
                        "missing_fields": missing,
                    },
                )
            )
            continue

        reviewed_at = _parse_policy_date(skill.reviewed_at)
        expires_at = _parse_policy_date(skill.expires_at)
        if reviewed_at is None or expires_at is None:
            diagnostics.append(
                Diagnostic.from_rule(
                    "SO015",
                    f"Skill '{skill.id}' has invalid review-window dates; expected YYYY-MM-DD.",
                    file=rel,
                    line=1,
                    skill_id=skill.id,
                    suggested_fix="Use ISO dates such as reviewed_at: 2026-06-21 and expires_at: 2026-12-21.",
                    metadata={
                        "policy_pack": ENGINEERING_GRADE_PACK,
                        "reviewed_at": skill.reviewed_at,
                        "expires_at": skill.expires_at,
                    },
                )
            )
            continue

        if expires_at < reviewed_at:
            diagnostics.append(
                Diagnostic.from_rule(
                    "SO015",
                    f"Skill '{skill.id}' expires_at is earlier than reviewed_at.",
                    file=rel,
                    line=1,
                    skill_id=skill.id,
                    suggested_fix="Set expires_at to a date after reviewed_at.",
                    metadata={
                        "policy_pack": ENGINEERING_GRADE_PACK,
                        "reviewed_at": skill.reviewed_at,
                        "expires_at": skill.expires_at,
                    },
                )
            )
        elif expires_at < today:
            diagnostics.append(
                Diagnostic.from_rule(
                    "SO016",
                    f"Skill '{skill.id}' review window expired on {skill.expires_at}.",
                    file=rel,
                    line=1,
                    skill_id=skill.id,
                    suggested_fix="Review the skill, update reviewed_at, and set a future expires_at date.",
                    metadata={
                        "policy_pack": ENGINEERING_GRADE_PACK,
                        "expires_at": skill.expires_at,
                    },
                )
            )
    return diagnostics


def _parse_policy_date(value: str) -> date | None:
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _is_external_source(source: str) -> bool:
    return urlparse(source).scheme.lower() in {"http", "https"}


def _normalize_license_id(value: str) -> str:
    cleaned = value.strip()
    if cleaned.lower() == "mit":
        return "MIT"
    if cleaned.lower() == "apache-2.0":
        return "Apache-2.0"
    return cleaned


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
