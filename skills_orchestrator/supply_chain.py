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


def verify_container_release(
    *,
    provenance_path: str | Path,
    sbom_path: str | Path | None = None,
    expected_image: str = "",
    expected_tag: str = "",
    expected_digest: str = "",
) -> dict[str, Any]:
    """Verify local container release provenance and optional expected subject facts."""
    path = Path(provenance_path)
    provenance = json.loads(path.read_text(encoding="utf-8"))
    checks: list[dict[str, Any]] = []

    image = provenance.get("image") or {}
    attestations = provenance.get("attestations") or {}
    provenance_subject = attestations.get("provenance_subject") or {}
    sbom_subject = attestations.get("sbom_subject") or {}
    sbom = provenance.get("sbom") or {}

    actual_image = str(image.get("name") or "")
    actual_tag = str(image.get("tag") or "")
    actual_digest = str(image.get("digest") or "")
    actual_reference = str(image.get("reference") or "")

    _add_check(
        checks,
        "image-digest-format",
        bool(_DIGEST_RE.fullmatch(actual_digest)),
        expected="sha256:<64 lowercase hex chars>",
        actual=actual_digest,
    )
    _add_check(
        checks,
        "image-reference",
        actual_reference == f"{actual_image}@{actual_digest}",
        expected=f"{actual_image}@{actual_digest}",
        actual=actual_reference,
    )
    _add_check(
        checks,
        "provenance-subject",
        provenance_subject.get("subject_name") == actual_image
        and provenance_subject.get("subject_digest") == actual_digest
        and bool(_DIGEST_RE.fullmatch(str(provenance_subject.get("subject_digest") or ""))),
        expected={"subject_name": actual_image, "subject_digest": actual_digest},
        actual=provenance_subject,
    )
    _add_check(
        checks,
        "sbom-subject",
        sbom_subject.get("subject_name") == actual_image
        and sbom_subject.get("subject_digest") == actual_digest
        and bool(_DIGEST_RE.fullmatch(str(sbom_subject.get("subject_digest") or ""))),
        expected={"subject_name": actual_image, "subject_digest": actual_digest},
        actual=sbom_subject,
    )

    if expected_image:
        _add_check(
            checks,
            "expected-image",
            actual_image == expected_image,
            expected=expected_image,
            actual=actual_image,
        )
    if expected_tag:
        _add_check(
            checks,
            "expected-tag",
            actual_tag == expected_tag,
            expected=expected_tag,
            actual=actual_tag,
        )
    if expected_digest:
        _validate_digest(expected_digest)
        _add_check(
            checks,
            "expected-digest",
            actual_digest == expected_digest,
            expected=expected_digest,
            actual=actual_digest,
        )

    resolved_sbom_path = _resolve_sbom_path(path, sbom_path, sbom)
    if resolved_sbom_path and sbom.get("sha256"):
        actual_hash = _file_sha256(resolved_sbom_path)
        _add_check(
            checks,
            "sbom-sha256",
            actual_hash == sbom.get("sha256"),
            expected=sbom.get("sha256"),
            actual=actual_hash,
            path=str(resolved_sbom_path),
        )
    elif sbom.get("sha256"):
        _add_check(
            checks,
            "sbom-sha256",
            False,
            expected=sbom.get("sha256"),
            actual="missing sbom file",
        )

    failed = sum(1 for check in checks if check["status"] == "fail")
    return {
        "schema_version": "skills-orchestrator.container-release-verification.v1",
        "tool": {"name": "skills-orchestrator", "version": __version__},
        "status": "fail" if failed else "pass",
        "summary": {"passed": len(checks) - failed, "failed": failed},
        "provenance": str(path),
        "checks": checks,
    }


def format_container_release_verification(report: dict[str, Any]) -> str:
    """Render release verification report as stable JSON."""
    return json.dumps(report, ensure_ascii=False, indent=2) + "\n"


def build_slsa_readiness(
    *,
    release_version: str = "",
    repository: str = "BambooGap/skills-orchestrator",
    image: str = "ghcr.io/bamboogap/skills-orchestrator",
    digest: str = "",
) -> dict[str, Any]:
    """Build a non-certifying SLSA readiness map for release evidence."""
    normalized_version = release_version or __version__
    tag = normalized_version if normalized_version.startswith("v") else f"v{normalized_version}"
    subject: dict[str, Any] = {
        "release": tag,
        "repository": repository,
        "image": image,
    }
    if digest:
        _validate_digest(digest)
        subject["digest"] = digest

    controls = [
        _readiness_control(
            "build-l1.provenance-exists",
            "pass",
            "Release workflows publish provenance attestations for PyPI artifacts and GHCR images.",
            [
                "PyPI wheel and sdist artifact attestations",
                "GHCR build provenance attestation bound to the image digest",
                "post-release-smoke.json retained as release evidence",
            ],
        ),
        _readiness_control(
            "build-l1.consistent-build-process",
            "pass",
            "Release tags are built by pinned GitHub Actions workflows with pre-publish checks.",
            [
                "release-triggered PyPI workflow",
                "release-triggered GHCR workflow",
                "CI matrix and package metadata checks before publish",
            ],
        ),
        _readiness_control(
            "build-l2.hosted-build-platform",
            "pass",
            "Release artifacts are produced by GitHub-hosted Actions workflows rather than a local workstation.",
            [
                "PyPI trusted publishing workflow",
                "GHCR publish workflow",
                "GitHub Artifact Attestations",
            ],
        ),
        _readiness_control(
            "build-l2.authenticated-provenance",
            "pass",
            "Consumers can verify artifact attestations and image signatures against GitHub workflow identity.",
            [
                "PyPI artifact attestations",
                "GHCR provenance and SBOM attestations",
                "Sigstore Cosign keyless image signature",
                "gh attestation verify consumer commands",
            ],
        ),
        _readiness_control(
            "build-l3.hardened-isolation",
            "not_claimed",
            "The project has not completed an independent SLSA Build L3 assessment of build-platform isolation.",
            [],
            [
                "No formal SLSA Build L3 claim",
                "No independent assessment that every provenance field is generated or verified by a trusted control plane",
                "No claim that build steps are unable to influence all future build state beyond GitHub-hosted runner guarantees",
            ],
        ),
        _readiness_control(
            "source-track",
            "not_claimed",
            "The project does not currently claim SLSA Source track conformance.",
            [],
            [
                "No machine-readable source-track verification summary attestation",
                "No formal source-control-system assessment",
            ],
        ),
    ]

    return {
        "schema_version": "skills-orchestrator.slsa-readiness.v1",
        "tool": {"name": "skills-orchestrator", "version": __version__},
        "generated_at": _now_iso(),
        "standard": {
            "name": "SLSA",
            "version": "v1.2",
            "url": "https://slsa.dev/spec/v1.2/build-requirements",
        },
        "subject": subject,
        "status": "readiness-mapped",
        "summary": {
            "build_l1": "evidence-ready",
            "build_l2": "evidence-ready",
            "build_l3": "not-claimed",
            "source_track": "not-claimed",
            "formal_claim": False,
        },
        "controls": controls,
        "consumer_verification": [
            {
                "id": "pypi-attestations",
                "description": "Verify PyPI wheel and sdist artifact attestations before promoting a production pin.",
                "document": "docs/supply-chain-verification.md#verify-pypi-artifacts",
            },
            {
                "id": "ghcr-provenance",
                "description": "Verify GHCR provenance attestation against the release tag and workflow identity.",
                "document": "docs/supply-chain-verification.md#verify-ghcr-provenance-and-sbom",
            },
            {
                "id": "ghcr-signature",
                "description": "Verify the GHCR digest Cosign signature against the release workflow identity.",
                "document": "docs/supply-chain-verification.md#verify-ghcr-image-signature",
            },
            {
                "id": "post-release-smoke",
                "description": "Retain the full post-release smoke report with zero failed checks.",
                "document": "docs/release-verification.md#post-release-smoke",
            },
        ],
        "not_claimed": [
            "formal SLSA certification or level declaration",
            "SLSA Build L3 hardened builder assessment",
            "SLSA Source track conformance",
            "runtime admission control",
            "tenant, budget, secret, or worker isolation",
        ],
    }


def format_slsa_readiness_json(report: dict[str, Any]) -> str:
    """Render SLSA readiness JSON with stable formatting."""
    return json.dumps(report, ensure_ascii=False, indent=2) + "\n"


def _readiness_control(
    control_id: str,
    status: str,
    description: str,
    evidence: list[str],
    gaps: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "id": control_id,
        "status": status,
        "description": description,
        "evidence": evidence,
        "gaps": gaps or [],
    }


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


def _add_check(
    checks: list[dict[str, Any]],
    check_id: str,
    ok: bool,
    *,
    expected: Any,
    actual: Any,
    **extra: Any,
) -> None:
    checks.append(
        {
            "id": check_id,
            "status": "pass" if ok else "fail",
            "expected": expected,
            "actual": actual,
            **extra,
        }
    )


def _resolve_sbom_path(
    provenance_path: Path,
    sbom_path: str | Path | None,
    sbom: dict[str, Any],
) -> Path | None:
    if sbom_path:
        path = Path(sbom_path)
    elif sbom.get("path"):
        path = Path(str(sbom["path"]))
    else:
        return None
    if not path.is_absolute():
        candidates = [
            (Path.cwd() / path).resolve(),
            (provenance_path.parent / path).resolve(),
            (provenance_path.parent / path.name).resolve(),
        ]
        return next((candidate for candidate in candidates if candidate.is_file()), None)
    return path if path.is_file() else None


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
