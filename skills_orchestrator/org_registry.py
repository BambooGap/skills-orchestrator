"""Organization-level registry export for multiple skill configs."""

from __future__ import annotations

import glob
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from skills_orchestrator import __version__
from skills_orchestrator.compiler import Parser, Resolver
from skills_orchestrator.compiler.instruction_manifest import build_instruction_manifest


def build_registry(
    config_globs: tuple[str, ...] | list[str], *, zone_id: str | None = None
) -> dict:
    """Build a deterministic registry from one or more skills.yaml globs."""
    config_paths = _expand_config_globs(config_globs)
    configs = [_config_entry(path, zone_id=zone_id) for path in config_paths]
    skill_ids = [skill["id"] for config in configs for skill in config["skills"]]
    duplicates = {
        skill_id: count for skill_id, count in sorted(Counter(skill_ids).items()) if count > 1
    }
    owners: dict[str, int] = defaultdict(int)
    for config in configs:
        for skill in config["skills"]:
            owner = skill["governance"].get("owner") or "(unowned)"
            owners[owner] += 1

    return {
        "schema_version": "skills-orchestrator.registry.v1",
        "generated_at": _now_iso(),
        "tool": {"name": "skills-orchestrator", "version": __version__},
        "summary": {
            "configs": len(configs),
            "skill_refs": len(skill_ids),
            "unique_skills": len(set(skill_ids)),
            "duplicate_skill_ids": len(duplicates),
        },
        "duplicates": duplicates,
        "owners": dict(sorted(owners.items())),
        "configs": configs,
    }


def write_registry(registry: dict, output_path: str) -> None:
    """Write registry JSON to a file."""
    Path(output_path).write_text(
        json.dumps(registry, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def diff_registries(base: dict, head: dict) -> dict[str, Any]:
    """Diff two registry payloads by registry entity and content/governance facts."""
    base_skills = _skills_by_key(base)
    head_skills = _skills_by_key(head)
    base_keys = set(base_skills)
    head_keys = set(head_skills)

    changed: list[dict[str, Any]] = []
    for registry_key in sorted(base_keys & head_keys):
        before = base_skills[registry_key]
        after = head_skills[registry_key]
        changes = {}
        if before.get("content_hash") != after.get("content_hash"):
            changes["content_hash"] = {
                "before": before.get("content_hash"),
                "after": after.get("content_hash"),
            }
        if before.get("governance") != after.get("governance"):
            changes["governance"] = {
                "before": before.get("governance"),
                "after": after.get("governance"),
            }
        if before.get("status") != after.get("status"):
            changes["status"] = {"before": before.get("status"), "after": after.get("status")}
        if changes:
            changed.append(
                {
                    "registry_key": registry_key,
                    "id": after["id"],
                    "changes": changes,
                }
            )

    duplicate_id_changes = _duplicate_id_changes(base, head)

    return {
        "schema_version": "skills-orchestrator.registry-diff.v1",
        "summary": {
            "added": len(head_keys - base_keys),
            "removed": len(base_keys - head_keys),
            "changed": len(changed),
            "duplicate_id_changes": len(duplicate_id_changes),
        },
        "added": [head_skills[key] for key in sorted(head_keys - base_keys)],
        "removed": [base_skills[key] for key in sorted(base_keys - head_keys)],
        "changed": changed,
        "duplicate_id_changes": duplicate_id_changes,
    }


def _expand_config_globs(config_globs: tuple[str, ...] | list[str]) -> list[str]:
    patterns = list(config_globs) or ["config/skills.yaml"]
    paths: list[str] = []
    for pattern in patterns:
        matches = sorted(glob.glob(pattern, recursive=True))
        if not matches and Path(pattern).exists():
            matches = [pattern]
        paths.extend(matches)
    unique = sorted({str(Path(path)) for path in paths if Path(path).is_file()})
    if not unique:
        raise FileNotFoundError("No skills config files matched the provided --config-glob values.")
    return unique


def _config_entry(config_path: str, *, zone_id: str | None) -> dict[str, Any]:
    parser = Parser(config_path)
    cfg = parser.parse()
    target_zone = None
    if zone_id:
        target_zone = next((zone for zone in cfg.zones if zone.id == zone_id), None)
        if target_zone is None:
            raise ValueError(f"Zone '{zone_id}' does not exist in {config_path}")
    resolved = Resolver(cfg).resolve(target_zone)
    manifest = build_instruction_manifest(config_path, cfg, resolved)
    config_display_path = str(Path(config_path))
    return {
        "path": config_display_path,
        "base_dir": cfg.base_dir,
        "zone": manifest["zone"],
        "summary": manifest["summary"],
        "skills": [
            {
                "registry_key": _registry_key(config_display_path, skill["id"], skill["path"]),
                "id": skill["id"],
                "name": skill["name"],
                "status": skill["status"],
                "path": skill["path"],
                "governance": skill["governance"],
                "content_hash": skill["content_hash"],
                "missing_file": skill["missing_file"],
            }
            for skill in manifest["skills"]
        ],
    }


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _skills_by_key(registry: dict) -> dict[str, dict[str, Any]]:
    skills: dict[str, dict[str, Any]] = {}
    for config in registry.get("configs", []):
        for skill in config.get("skills", []):
            key = skill.get("registry_key") or _registry_key(
                config.get("path", ""), skill["id"], skill.get("path", "")
            )
            skills[key] = {**skill, "registry_key": key}
    return skills


def _registry_key(config_path: str, skill_id: str, skill_path: str) -> str:
    return f"{config_path}::{skill_path}::{skill_id}"


def _duplicate_id_changes(base: dict, head: dict) -> list[dict[str, Any]]:
    base_duplicates = base.get("duplicates", {})
    head_duplicates = head.get("duplicates", {})
    changed = []
    for skill_id in sorted(set(base_duplicates) | set(head_duplicates)):
        before = base_duplicates.get(skill_id, 1)
        after = head_duplicates.get(skill_id, 1)
        if before != after:
            changed.append({"id": skill_id, "before": before, "after": after})
    return changed
