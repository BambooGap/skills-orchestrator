"""Provenance integrity helpers for local skill content."""

from __future__ import annotations

import hashlib
import re

from skills_orchestrator.models import SkillMeta

_SHA256_PROVENANCE_RE = re.compile(r"^sha256:([0-9a-f]{64})$")


def validate_provenance_content_hash(skill: SkillMeta, raw_content: str) -> None:
    """Fail closed when imported skill content no longer matches recorded provenance.

    The provenance hash is bound to the raw skill file bytes, before base inheritance
    content is merged. Import provenance is generated from the fetched file itself, so
    checking the raw local file preserves that contract across build, sync, MCP, and
    pipeline content reads.
    """
    expected = str(skill.provenance.get("content_hash", "")).strip()
    if not expected:
        return

    match = _SHA256_PROVENANCE_RE.fullmatch(expected)
    if not match:
        raise ValueError(
            f"Skill '{skill.id}' has invalid provenance.content_hash format: {expected!r}"
        )

    actual = hashlib.sha256(raw_content.encode("utf-8")).hexdigest()
    if actual != match.group(1):
        raise ValueError(
            f"Skill '{skill.id}' provenance.content_hash mismatch for {skill.path}: "
            f"expected sha256:{match.group(1)[:12]}..., got sha256:{actual[:12]}..."
        )
