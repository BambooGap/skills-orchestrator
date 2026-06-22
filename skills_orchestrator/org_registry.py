"""Organization-level registry export for multiple skill configs."""

from __future__ import annotations

import glob
import html
import json
import re
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


def build_registry_graph(registry: dict[str, Any]) -> dict[str, Any]:
    """Build a structural governance graph from a registry payload."""
    nodes: dict[str, dict[str, Any]] = {}
    edges: dict[str, dict[str, Any]] = {}

    def add_node(node_id: str, node_type: str, label: str, **properties: Any) -> None:
        existing = nodes.get(node_id)
        payload = {
            "id": node_id,
            "type": node_type,
            "label": label,
            "properties": {
                key: value for key, value in properties.items() if value not in (None, "")
            },
        }
        if existing:
            existing["properties"].update(payload["properties"])
            return
        nodes[node_id] = payload

    def add_edge(
        source: str, target: str, edge_type: str, label: str | None = None, **properties: Any
    ) -> None:
        edge_id = f"{source}::{edge_type}::{target}"
        edges[edge_id] = {
            "id": edge_id,
            "source": source,
            "target": target,
            "type": edge_type,
            "label": label or edge_type,
            "properties": {
                key: value for key, value in properties.items() if value not in (None, "")
            },
        }

    for config in registry.get("configs", []):
        config_path = config.get("path", "")
        config_id = _graph_id("config", config_path)
        add_node(
            config_id,
            "config",
            config_path or "config",
            path=config_path,
            base_dir=config.get("base_dir", ""),
            summary=config.get("summary", {}),
        )

        zone = config.get("zone") or {}
        zone_id = _graph_id("zone", f"{config_path}:{zone.get('id', 'default')}")
        add_node(
            zone_id,
            "zone",
            zone.get("id", "default"),
            name=zone.get("name", ""),
            load_policy=zone.get("load_policy", ""),
            priority=zone.get("priority", 0),
        )
        add_edge(config_id, zone_id, "config_uses_zone")

        skills_by_id: dict[str, str] = {}
        for skill in config.get("skills", []):
            registry_key = skill.get("registry_key") or _registry_key(
                config_path, skill.get("id", ""), skill.get("path", "")
            )
            skill_id = _graph_id("skill", registry_key)
            skills_by_id[skill.get("id", "")] = skill_id
            governance = skill.get("governance") or {}
            add_node(
                skill_id,
                "skill",
                skill.get("id", ""),
                registry_key=registry_key,
                name=skill.get("name", ""),
                status=skill.get("status", ""),
                path=skill.get("path", ""),
                tags=skill.get("tags", []),
                priority=skill.get("priority"),
                content_hash=skill.get("content_hash", {}),
                missing_file=skill.get("missing_file", False),
                lifecycle=governance.get("lifecycle", ""),
                license=governance.get("license", ""),
            )
            add_edge(config_id, skill_id, "config_contains_skill", status=skill.get("status", ""))

            owner = governance.get("owner") or "(unowned)"
            owner_id = _graph_id("owner", owner)
            add_node(owner_id, "owner", owner, skill_count=registry.get("owners", {}).get(owner))
            add_edge(skill_id, owner_id, "skill_owned_by")

            source = governance.get("source", "")
            if source:
                source_id = _graph_id("source", source)
                add_node(source_id, "source", source)
                add_edge(skill_id, source_id, "skill_sourced_from")

        for combo in config.get("combos", []):
            combo_id = _graph_id("combo", f"{config_path}:{combo.get('id', '')}")
            add_node(
                combo_id,
                "combo",
                combo.get("id", ""),
                name=combo.get("name", ""),
                description=combo.get("description", ""),
            )
            add_edge(config_id, combo_id, "config_defines_combo")
            for member in combo.get("members", []):
                member_node = skills_by_id.get(member)
                if member_node:
                    add_edge(member_node, combo_id, "skill_member_of_combo")

        for skill in config.get("skills", []):
            source_node = skills_by_id.get(skill.get("id", ""))
            if not source_node:
                continue
            for conflict_id in skill.get("conflict_with", []):
                target_node = skills_by_id.get(conflict_id)
                if target_node:
                    add_edge(source_node, target_node, "skill_conflicts_with")

    return {
        "schema_version": "skills-orchestrator.registry-graph.v1",
        "generated_at": _now_iso(),
        "tool": registry.get("tool", {"name": "skills-orchestrator", "version": __version__}),
        "summary": {
            "nodes": len(nodes),
            "edges": len(edges),
            "configs": registry.get("summary", {}).get("configs", 0),
            "skill_refs": registry.get("summary", {}).get("skill_refs", 0),
        },
        "nodes": [nodes[key] for key in sorted(nodes)],
        "edges": [edges[key] for key in sorted(edges)],
    }


def write_registry_graph(graph: dict[str, Any], output_path: str) -> None:
    """Write registry graph JSON to a file."""
    Path(output_path).write_text(
        json.dumps(graph, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
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
                    "skill": _changed_skill_snapshot(after),
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


def format_registry_diff_markdown(diff: dict[str, Any]) -> str:
    """Render a registry diff as PR-review-friendly Markdown."""
    summary = diff.get("summary", {})
    lines = [
        "# Registry Diff",
        "",
        "## Summary",
        "",
        "| Metric | Count |",
        "|---|---:|",
        f"| Added | {summary.get('added', 0)} |",
        f"| Removed | {summary.get('removed', 0)} |",
        f"| Changed | {summary.get('changed', 0)} |",
        f"| Duplicate skill ID changes | {summary.get('duplicate_id_changes', 0)} |",
        "",
    ]
    lines.extend(_skills_table("Changed Skills", _changed_rows(diff.get("changed", []))))
    lines.extend(_skills_table("Added Skills", _skill_rows(diff.get("added", []))))
    lines.extend(_skills_table("Removed Skills", _skill_rows(diff.get("removed", []))))
    lines.extend(_duplicate_changes_table(diff.get("duplicate_id_changes", [])))
    return "\n".join(lines).rstrip() + "\n"


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
        "combos": manifest["combos"],
        "skills": [
            {
                "registry_key": _registry_key(config_display_path, skill["id"], skill["path"]),
                "id": skill["id"],
                "name": skill["name"],
                "status": skill["status"],
                "path": skill["path"],
                "source_load_policy": skill["source_load_policy"],
                "effective_load_policy": skill["effective_load_policy"],
                "priority": skill["priority"],
                "zones": skill["zones"],
                "tags": skill["tags"],
                "base": skill["base"],
                "conflict_with": skill["conflict_with"],
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


def _graph_id(node_type: str, value: str) -> str:
    return f"{node_type}:{value}"


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


def _skills_table(title: str, rows: list[list[str]]) -> list[str]:
    lines = [f"## {title}", ""]
    if not rows:
        return [*lines, "No entries.", ""]
    lines.extend(
        [
            "| Skill | Status | Owner | Path | Registry key | Details |",
            "|---|---|---|---|---|---|",
        ]
    )
    for row in rows:
        lines.append("| " + " | ".join(_escape_markdown_cell(cell) for cell in row) + " |")
    lines.append("")
    return lines


def _skill_rows(skills: list[dict[str, Any]]) -> list[list[str]]:
    rows = []
    for skill in skills:
        governance = skill.get("governance") or {}
        rows.append(
            [
                skill.get("id", ""),
                skill.get("status", ""),
                governance.get("owner", ""),
                _redact_path_like(skill.get("path", "")),
                _redact_registry_key(skill.get("registry_key", "")),
                skill.get("name", ""),
            ]
        )
    return rows


def _changed_rows(changed: list[dict[str, Any]]) -> list[list[str]]:
    rows = []
    for item in changed:
        change_fields = ", ".join(sorted(item.get("changes", {})))
        details = _change_details(item.get("changes", {}))
        skill = item.get("skill") or {}
        governance = skill.get("governance") or {}
        rows.append(
            [
                item.get("id", ""),
                skill.get("status") or "changed",
                governance.get("owner") or _changed_owner_fallback(item.get("changes", {})),
                _redact_path_like(skill.get("path") or _path_from_registry_key(item)),
                _redact_registry_key(item.get("registry_key", "")),
                f"{change_fields}: {details}" if details else change_fields,
            ]
        )
    return rows


def _changed_skill_snapshot(skill: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": skill.get("name", ""),
        "status": skill.get("status", ""),
        "path": skill.get("path", ""),
        "governance": skill.get("governance") or {},
    }


def _changed_owner_fallback(changes: dict[str, Any]) -> str:
    governance = changes.get("governance") or {}
    after_governance = governance.get("after") or {}
    return after_governance.get("owner", "")


def _path_from_registry_key(item: dict[str, Any]) -> str:
    parts = str(item.get("registry_key", "")).split("::")
    return parts[1] if len(parts) >= 3 else ""


def _change_details(changes: dict[str, Any]) -> str:
    detail_parts = []
    governance = changes.get("governance")
    if governance:
        before_governance = governance.get("before") or {}
        after_governance = governance.get("after") or {}
        for field in (
            "owner",
            "source",
            "version",
            "lifecycle",
            "approvers",
            "reviewed_at",
            "expires_at",
            "license",
            "provenance",
        ):
            before_value = _governance_value(before_governance.get(field))
            after_value = _governance_value(after_governance.get(field))
            if before_value != after_value:
                detail_parts.append(f"{field} {before_value} -> {after_value}")
    status = changes.get("status")
    if status:
        detail_parts.append(f"status {status.get('before', '')} -> {status.get('after', '')}")
    content_hash = changes.get("content_hash")
    if content_hash:
        before_hash = _hash_short(content_hash.get("before"))
        after_hash = _hash_short(content_hash.get("after"))
        detail_parts.append(f"hash {before_hash} -> {after_hash}")
    return "; ".join(detail_parts)


def _governance_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return ", ".join(str(item) for item in value)
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return str(value)


def _duplicate_changes_table(changes: list[dict[str, Any]]) -> list[str]:
    lines = ["## Duplicate Skill ID Changes", ""]
    if not changes:
        return [*lines, "No entries.", ""]
    lines.extend(["| Skill ID | Before | After |", "|---|---:|---:|"])
    for item in changes:
        lines.append(
            "| "
            + " | ".join(
                _escape_markdown_cell(str(value))
                for value in (item.get("id", ""), item.get("before", ""), item.get("after", ""))
            )
            + " |"
        )
    lines.append("")
    return lines


def _hash_short(value: Any) -> str:
    if isinstance(value, dict):
        value = value.get("value", "")
    if not value:
        return ""
    return str(value)[:12]


def _escape_markdown_cell(value: Any) -> str:
    text = "" if value is None else str(value)
    text = _strip_control_chars(text)
    text = html.escape(text, quote=False)
    text = text.replace("\\", "\\\\").replace("|", "\\|").replace("\n", "<br>")
    if not text:
        return ""
    return f"<code>{text}</code>"


def _redact_registry_key(value: Any) -> str:
    text = "" if value is None else str(value)
    return "::".join(_redact_path_like(part) for part in text.split("::"))


def _redact_path_like(value: Any) -> str:
    text = "" if value is None else str(value)
    if not text:
        return ""
    if not text.startswith(("/", "~")):
        return text
    name = Path(text).name
    return f".../{name}" if name else "..."


def _strip_control_chars(value: str) -> str:
    return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", value)
