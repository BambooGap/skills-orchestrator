"""Software supply-chain evidence helpers."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from importlib import metadata
from typing import Any
from uuid import NAMESPACE_URL, uuid5

from skills_orchestrator import __version__


def build_python_package_sbom(
    *,
    project_name: str = "skills-orchestrator",
    include_dependencies: bool = True,
) -> dict[str, Any]:
    """Build a small CycloneDX SBOM for the installed Python package.

    The existing instruction manifest CycloneDX export describes governed skill
    assets. This SBOM describes the software package dependency surface.
    """
    project_version = _distribution_version(project_name) or __version__
    components = []
    if include_dependencies:
        components = [
            {
                "type": "library",
                "bom-ref": f"pkg:pypi/{name}@{version}",
                "name": name,
                "version": version,
                "purl": f"pkg:pypi/{name}@{version}",
            }
            for name, version in _installed_dependencies(project_name)
        ]

    serial = uuid5(NAMESPACE_URL, f"pkg:pypi/{project_name}@{project_version}")
    return {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "serialNumber": f"urn:uuid:{serial}",
        "version": 1,
        "metadata": {
            "timestamp": _now_iso(),
            "tools": [
                {
                    "vendor": "BambooGap",
                    "name": "skills-orchestrator",
                    "version": __version__,
                }
            ],
            "component": {
                "type": "application",
                "bom-ref": f"pkg:pypi/{project_name}@{project_version}",
                "name": project_name,
                "version": project_version,
                "purl": f"pkg:pypi/{project_name}@{project_version}",
            },
        },
        "components": components,
    }


def format_sbom_json(sbom: dict[str, Any]) -> str:
    """Render SBOM JSON with stable formatting."""
    return json.dumps(sbom, ensure_ascii=False, indent=2) + "\n"


def _installed_dependencies(project_name: str) -> list[tuple[str, str]]:
    try:
        dist = metadata.distribution(project_name)
    except metadata.PackageNotFoundError:
        return []

    names = set()
    for requirement in dist.requires or []:
        name = _runtime_requirement_name(requirement)
        if not name:
            continue
        names.add(name)

    dependencies = []
    for name in sorted(names, key=str.lower):
        version = _distribution_version(name)
        if version:
            dependencies.append((name, version))
    return dependencies


def _distribution_version(name: str) -> str | None:
    try:
        return metadata.version(name)
    except metadata.PackageNotFoundError:
        return None


def _runtime_requirement_name(requirement: str) -> str | None:
    marker = requirement.split(";", 1)[1].lower() if ";" in requirement else ""
    if "extra" in marker:
        return None
    name = requirement.split(";", 1)[0].split("[", 1)[0].strip()
    match = re.match(r"^[A-Za-z0-9_.-]+", name)
    return match.group(0) if match else None


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
