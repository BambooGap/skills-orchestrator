"""Instruction inventory export for agent skills."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from skills_orchestrator import __version__
from skills_orchestrator.compiler.policies import compute_effective_load_policy
from skills_orchestrator.models import Config, ResolvedConfig, SkillMeta


def build_instruction_manifest(config_path: str, cfg: Config, resolved: ResolvedConfig) -> dict:
    """Build a native instruction manifest from resolver output.

    The resolver remains the source of truth for zone filtering and conflict decisions.
    This function serializes those facts without re-deciding policy.
    """
    skills = [
        *_skill_entries(resolved.forced_skills, "forced", resolved),
        *_skill_entries(resolved.passive_skills, "passive", resolved),
        *_skill_entries(resolved.blocked_skills, "blocked", resolved),
    ]
    zone = resolved.active_zone
    return {
        "schema_version": "1.0",
        "generated_at": _now_iso(),
        "tool": {"name": "skills-orchestrator", "version": __version__},
        "config": {
            "path": config_path,
            "base_dir": cfg.base_dir,
        },
        "zone": {
            "id": zone.id if zone else "default",
            "name": zone.name if zone else "default",
            "load_policy": zone.load_policy if zone else "free",
            "priority": zone.priority if zone else 0,
            "skills": list(zone.skills) if zone else [],
            "allow_base_skills": list(zone.allow_base_skills) if zone else [],
        },
        "summary": {
            "total": len(skills),
            "forced": len(resolved.forced_skills),
            "passive": len(resolved.passive_skills),
            "blocked": len(resolved.blocked_skills),
            "combos": len(cfg.combos),
        },
        "skills": skills,
        "combos": [
            {
                "id": combo.id,
                "name": combo.name,
                "members": list(combo.members),
                "description": combo.description,
            }
            for combo in cfg.combos
        ],
    }


def _skill_entries(
    skills: list[SkillMeta], status: str, resolved: ResolvedConfig
) -> list[dict[str, Any]]:
    zone = resolved.active_zone
    zone_forces_all = zone is not None and zone.load_policy == "require"
    return [
        _skill_entry(skill, status, resolved.base_dir, zone_forces_all, resolved.block_reasons)
        for skill in skills
    ]


def _skill_entry(
    skill: SkillMeta,
    status: str,
    base_dir: str,
    zone_forces_all: bool,
    block_reasons: dict,
) -> dict[str, Any]:
    path = _resolve_skill_path(skill.path, base_dir)
    content_hash, size_bytes, missing_file = _file_facts(path)
    return {
        "id": skill.id,
        "name": skill.name,
        "summary": skill.summary,
        "path": skill.path,
        "status": status,
        "source_load_policy": skill.load_policy,
        "effective_load_policy": compute_effective_load_policy(skill, zone_forces_all),
        "priority": skill.priority,
        "zones": list(skill.zones),
        "tags": list(skill.tags),
        "base": skill.base,
        "conflict_with": list(skill.conflict_with),
        "governance": {
            "owner": skill.owner,
            "source": skill.source,
            "version": skill.version,
            "lifecycle": skill.lifecycle,
            "approvers": list(skill.approvers),
            "reviewed_at": skill.reviewed_at,
            "expires_at": skill.expires_at,
        },
        "metadata": dict(skill.metadata),
        "block_reason": block_reasons.get(skill.id, ""),
        "content_hash": {"alg": "SHA-256", "value": content_hash},
        "size_bytes": size_bytes,
        "missing_file": missing_file,
    }


def _resolve_skill_path(skill_path: str, base_dir: str) -> Path:
    path = Path(skill_path)
    if path.is_absolute():
        return path
    return (Path(base_dir) / path).resolve()


def _file_facts(path: Path) -> tuple[str, int, bool]:
    if not path.exists():
        return "", 0, True
    data = path.read_bytes()
    return hashlib.sha256(data).hexdigest(), len(data), False


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
