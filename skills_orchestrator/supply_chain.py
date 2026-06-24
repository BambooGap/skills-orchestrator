"""Software supply-chain evidence helpers."""

from __future__ import annotations

import json
import re
import hashlib
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path
from typing import Any
from uuid import NAMESPACE_URL, uuid5

from skills_orchestrator import __version__

_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


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


def build_container_image_sbom(
    *,
    image: str,
    tag: str,
    digest: str,
    project_name: str = "skills-orchestrator",
    include_dependencies: bool = True,
) -> dict[str, Any]:
    """Build a lightweight CycloneDX SBOM bound to a pushed container digest.

    This does not claim to scan operating-system layers. It records the
    SkillOps package dependency surface and binds it to the immutable OCI
    image digest that release attestation will use as the subject.
    """
    _validate_digest(digest)
    package_sbom = build_python_package_sbom(
        project_name=project_name,
        include_dependencies=include_dependencies,
    )
    project_version = package_sbom["metadata"]["component"]["version"]
    serial = uuid5(NAMESPACE_URL, f"pkg:oci/{image}@{digest}")
    package_component = dict(package_sbom["metadata"]["component"])
    package_component["scope"] = "required"

    return {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "serialNumber": f"urn:uuid:{serial}",
        "version": 1,
        "metadata": {
            "timestamp": _now_iso(),
            "tools": package_sbom["metadata"]["tools"],
            "component": {
                "type": "container",
                "bom-ref": f"pkg:oci/{image}@{digest}",
                "name": image,
                "version": tag or digest,
                "purl": f"pkg:oci/{image}@{digest}",
                "properties": [
                    {"name": "skillops:image.digest", "value": digest},
                    {"name": "skillops:package.name", "value": project_name},
                    {"name": "skillops:package.version", "value": project_version},
                ],
            },
        },
        "components": [package_component, *package_sbom["components"]],
    }


def build_container_release_provenance(
    *,
    image: str,
    tag: str,
    digest: str,
    repository: str = "",
    commit: str = "",
    workflow_run_url: str = "",
    sbom_path: str | Path | None = None,
) -> dict[str, Any]:
    """Build SkillOps release provenance tied to an OCI image digest."""
    _validate_digest(digest)
    sbom: dict[str, Any] | None = None
    if sbom_path:
        path = Path(sbom_path)
        sbom = {
            "path": str(path),
            "sha256": _file_sha256(path),
        }
    return {
        "schema_version": "skills-orchestrator.container-provenance.v1",
        "tool": {"name": "skills-orchestrator", "version": __version__},
        "generated_at": _now_iso(),
        "image": {
            "name": image,
            "tag": tag,
            "digest": digest,
            "reference": f"{image}@{digest}",
        },
        "source": {
            "repository": repository,
            "commit": commit,
            "workflow_run_url": workflow_run_url,
        },
        "attestations": {
            "provenance_subject": {
                "subject_name": image,
                "subject_digest": digest,
            },
            "sbom_subject": {
                "subject_name": image,
                "subject_digest": digest,
            },
        },
        "sbom": sbom,
    }


def format_sbom_json(sbom: dict[str, Any]) -> str:
    """Render SBOM JSON with stable formatting."""
    return json.dumps(sbom, ensure_ascii=False, indent=2) + "\n"


def format_provenance_json(provenance: dict[str, Any]) -> str:
    """Render container provenance JSON with stable formatting."""
    return json.dumps(provenance, ensure_ascii=False, indent=2) + "\n"


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


def _validate_digest(digest: str) -> None:
    if not _DIGEST_RE.fullmatch(digest):
        raise ValueError("container digest must use sha256:<64 lowercase hex chars>")


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
