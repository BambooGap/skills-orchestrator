"""Formatters for instruction manifests."""

from __future__ import annotations

import json
from typing import Any


def format_instruction_manifest_json(manifest: dict[str, Any]) -> str:
    """Return the native instruction manifest as stable JSON."""
    return json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"


def format_instruction_manifest_cyclonedx(manifest: dict[str, Any]) -> str:
    """Map the instruction manifest to an experimental CycloneDX BOM."""
    component_ref = "skills-orchestrator:instruction-set"
    skill_refs = [f"skill:{skill['id']}" for skill in manifest["skills"]]
    payload = {
        "bomFormat": "CycloneDX",
        "specVersion": "1.7",
        "version": 1,
        "metadata": {
            "timestamp": manifest["generated_at"],
            "tools": {
                "components": [
                    {
                        "type": "application",
                        "name": manifest["tool"]["name"],
                        "version": manifest["tool"]["version"],
                    }
                ]
            },
            "component": {
                "type": "data",
                "bom-ref": component_ref,
                "name": "skills-orchestrator instruction manifest",
                "version": manifest["tool"]["version"],
                "properties": _properties(
                    {
                        "schema_version": manifest["schema_version"],
                        "zone": manifest["zone"]["id"],
                        "format": "instruction-manifest-cyclonedx-experimental",
                    }
                ),
            },
        },
        "components": [_skill_component(skill) for skill in manifest["skills"]],
        "dependencies": [
            {"ref": component_ref, "dependsOn": skill_refs},
            *[
                {"ref": f"skill:{skill['id']}", "dependsOn": [f"skill:{skill['base']}"]}
                for skill in manifest["skills"]
                if skill.get("base")
            ],
        ],
        "properties": [
            *_properties(manifest["summary"], prefix="skills-orchestrator:summary"),
            {
                "name": "skills-orchestrator:combos",
                "value": json.dumps(manifest["combos"], ensure_ascii=False, separators=(",", ":")),
            },
            {
                "name": "skills-orchestrator:experimental",
                "value": "true",
            },
        ],
    }
    return json.dumps(payload, indent=2, ensure_ascii=False) + "\n"


def _skill_component(skill: dict[str, Any]) -> dict[str, Any]:
    component: dict[str, Any] = {
        "type": "data",
        "bom-ref": f"skill:{skill['id']}",
        "name": skill["name"],
        "description": skill["summary"],
        "properties": _skill_properties(skill),
    }
    content_hash = skill["content_hash"]["value"]
    if content_hash:
        component["hashes"] = [{"alg": "SHA-256", "content": content_hash}]
    return component


def _skill_properties(skill: dict[str, Any]) -> list[dict[str, str]]:
    values = {
        "id": skill["id"],
        "path": skill["path"],
        "status": skill["status"],
        "source_load_policy": skill["source_load_policy"],
        "effective_load_policy": skill["effective_load_policy"],
        "priority": skill["priority"],
        "zones": skill["zones"],
        "tags": skill["tags"],
        "base": skill["base"],
        "conflict_with": skill["conflict_with"],
        "governance": skill.get("governance", {}),
        "metadata": skill.get("metadata", {}),
        "block_reason": skill["block_reason"],
        "size_bytes": skill["size_bytes"],
        "missing_file": skill["missing_file"],
    }
    return _properties(values)


def _properties(
    values: dict[str, Any], prefix: str = "skills-orchestrator"
) -> list[dict[str, str]]:
    properties = []
    for key, value in values.items():
        if isinstance(value, (list, dict)):
            rendered = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        else:
            rendered = str(value)
        properties.append({"name": f"{prefix}:{key}", "value": rendered})
    return properties
