"""Export resolver facts for policy-as-code tools."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any

from skills_orchestrator import __version__
from skills_orchestrator.compiler.policies import compute_effective_load_policy
from skills_orchestrator.models import Config, ResolvedConfig, SkillMeta

REGO_PACKAGE_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)*$")


def build_opa_input(cfg: Config, resolved: ResolvedConfig) -> dict[str, Any]:
    """Build an OPA input document from authoritative resolver output."""
    zone = resolved.active_zone
    skills = [
        *_skill_entries(resolved.forced_skills, "forced", resolved),
        *_skill_entries(resolved.passive_skills, "passive", resolved),
        *_skill_entries(resolved.blocked_skills, "blocked", resolved),
    ]
    return {
        "schema_version": "1.0",
        "generated_at": _now_iso(),
        "tool": {"name": "skills-orchestrator", "version": __version__},
        "zone": {
            "id": zone.id if zone else "default",
            "name": zone.name if zone else "default",
            "load_policy": zone.load_policy if zone else "free",
            "priority": zone.priority if zone else 0,
            "skills": list(zone.skills) if zone else [],
            "allow_base_skills": list(zone.allow_base_skills) if zone else [],
        },
        "skills": skills,
        "resolution": {
            "forced": [skill.id for skill in resolved.forced_skills],
            "passive": [skill.id for skill in resolved.passive_skills],
            "blocked": [skill.id for skill in resolved.blocked_skills],
            "block_reasons": dict(resolved.block_reasons),
        },
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


def build_rego_test(opa_input: dict[str, Any], package: str = "skills_orchestrator_test") -> str:
    """Build a self-contained Rego test fixture for exported resolver facts."""
    if not REGO_PACKAGE_RE.fullmatch(package):
        raise ValueError("Rego package 只能包含字母、数字、下划线和点号，且不能以数字开头")
    fixture = json.dumps(opa_input, indent=2, ensure_ascii=False)
    return f"""package {package}

fixture := {fixture}

test_export_matches_resolver_resolution if {{
  forced_ids := [skill.id | skill := fixture.skills[_]; skill.status == "forced"]
  passive_ids := [skill.id | skill := fixture.skills[_]; skill.status == "passive"]
  blocked_ids := [skill.id | skill := fixture.skills[_]; skill.status == "blocked"]

  forced_ids == fixture.resolution.forced
  passive_ids == fixture.resolution.passive
  blocked_ids == fixture.resolution.blocked
}}

test_require_policy_matches_forced_resolution if {{
  require_ids := {{skill.id | skill := fixture.skills[_]; skill.status != "blocked"; skill.effective_load_policy == "require"}}
  forced_ids := {{id | id := fixture.resolution.forced[_]}}

  require_ids == forced_ids
}}

test_blocked_skills_have_resolver_reasons if {{
  blocked_ids := {{skill.id | skill := fixture.skills[_]; skill.status == "blocked"}}
  reason_ids := {{id | reason := fixture.resolution.block_reasons[id]; reason != ""}}

  blocked_ids == reason_ids
}}
"""


def _skill_entries(
    skills: list[SkillMeta], status: str, resolved: ResolvedConfig
) -> list[dict[str, Any]]:
    zone = resolved.active_zone
    zone_forces_all = zone is not None and zone.load_policy == "require"
    return [
        _skill_entry(skill, status, zone_forces_all, resolved.block_reasons) for skill in skills
    ]


def _skill_entry(
    skill: SkillMeta,
    status: str,
    zone_forces_all: bool,
    block_reasons: dict,
) -> dict[str, Any]:
    return {
        "id": skill.id,
        "name": skill.name,
        "path": skill.path,
        "summary": skill.summary,
        "tags": list(skill.tags),
        "status": status,
        "source_load_policy": skill.load_policy,
        "effective_load_policy": compute_effective_load_policy(skill, zone_forces_all),
        "priority": skill.priority,
        "zones": list(skill.zones),
        "conflict_with": list(skill.conflict_with),
        "base": skill.base,
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
    }


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
