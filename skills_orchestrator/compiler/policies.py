"""Shared load-policy computation — single source of truth.

All callers (Resolver, SkillsLock, SyncEngine) must use
compute_effective_load_policy() instead of duplicating this logic.
"""

from skills_orchestrator.models import SkillMeta


def compute_effective_load_policy(skill: SkillMeta, zone_forces_all: bool) -> str:
    """Return the effective load_policy for *skill* given the active zone.

    Rules:
    - skill.load_policy == "require"  → always "require"
    - zone_forces_all and skill.load_policy == "free"  → "require"
    - otherwise → skill.load_policy
    """
    if skill.load_policy == "require":
        return "require"
    if zone_forces_all and skill.load_policy == "free":
        return "require"
    return skill.load_policy
