"""Multi-repository evidence artifact indexing."""

from __future__ import annotations

import hashlib
import json
import os
from datetime import UTC, datetime
from glob import glob
from pathlib import Path
from typing import Any

from skills_orchestrator import __version__

SCHEMA_VERSION = "skills-orchestrator.multi-repo-artifacts.v1"

SCHEMA_KIND_BY_LABEL = {
    "adapter_inspect": "adapter-inspect",
    "check_json": "check",
    "ci_explainability": "ci-explainability",
    "doctor": "doctor",
    "instruction_manifest": "manifest",
    "opa_input": "policy-opa-input",
    "package_sbom": "supply-chain-sbom",
    "registry": "registry",
}


def expand_manifest_inputs(
    manifests: tuple[str, ...] | list[str] = (),
    manifest_globs: tuple[str, ...] | list[str] = (),
) -> list[str]:
    """Resolve explicit manifest specs and glob patterns in stable order."""
    specs = list(manifests)
    for pattern in manifest_globs:
        for match in sorted(glob(pattern, recursive=True)):
            specs.append(match)
    if not specs:
        raise ValueError("At least one --manifest or --manifest-glob input is required")
    return sorted(set(specs), key=_manifest_sort_key)


def build_multi_repo_artifacts(
    manifest_specs: tuple[str, ...] | list[str],
    *,
    scope_name: str | None = None,
    generated_at: str | None = None,
    previous_index_hash: str = "",
) -> dict[str, Any]:
    """Build a multi-repository artifact index from evidence manifests."""
    repositories = [_repository_entry(spec) for spec in manifest_specs]
    repositories.sort(key=lambda item: item["id"])
    duplicate_ids = sorted(
        repo_id
        for repo_id in {repository["id"] for repository in repositories}
        if sum(1 for repository in repositories if repository["id"] == repo_id) > 1
    )
    if duplicate_ids:
        raise ValueError(
            "Duplicate repository id(s) in evidence index: " + ", ".join(duplicate_ids)
        )
    artifacts = [
        artifact for repository in repositories for artifact in repository.pop("_artifacts")
    ]
    invalid = sum(1 for artifact in artifacts if artifact["status"] == "invalid")
    missing = sum(1 for artifact in artifacts if artifact["status"] == "missing")
    index = {
        "schema_version": SCHEMA_VERSION,
        "tool": {"name": "skills-orchestrator", "version": __version__},
        "generated_at": generated_at or _now_iso(),
        "scope": {
            "kind": "multi-repo",
            "name": scope_name or os.environ.get("GITHUB_REPOSITORY_OWNER") or "",
        },
        "summary": {
            "repositories": len(repositories),
            "artifacts": len(artifacts),
            "missing": missing,
            "invalid": invalid,
            "bundle_hashes": sum(
                1 for repository in repositories if repository["ledger"]["bundle_hash"]
            ),
            "policy_errors": sum(repository["policy"]["errors"] for repository in repositories),
            "policy_warnings": sum(repository["policy"]["warnings"] for repository in repositories),
            "registry_skills": sum(repository["registry"]["skills"] for repository in repositories),
        },
        "repositories": repositories,
        "artifacts": artifacts,
        "ledger": {
            "artifact_hashes": _index_artifact_hashes(artifacts),
            "previous_index_hash": previous_index_hash,
            "index_hash": "",
        },
    }
    index["ledger"]["index_hash"] = _index_hash(index)
    return index


def format_multi_repo_artifacts_json(index: dict[str, Any]) -> str:
    """Return canonical pretty JSON for multi-repository artifacts."""
    return json.dumps(index, ensure_ascii=False, indent=2) + "\n"


def _repository_entry(spec: str) -> dict[str, Any]:
    repo_id, manifest_path = _parse_manifest_spec(spec)
    manifest_path = manifest_path.expanduser()
    if not manifest_path.is_absolute():
        manifest_path = (Path.cwd() / manifest_path).resolve()
    manifest = _load_json(manifest_path)
    evidence_dir = manifest_path.parent
    repo_root = evidence_dir.parent
    repo_id = repo_id or repo_root.name

    files = manifest.get("files") or {}
    artifact_hashes = (manifest.get("ledger") or {}).get("artifact_hashes") or {}
    artifacts = [
        _artifact_entry(repo_id, manifest_path, label, raw_path, artifact_hashes.get(label) or {})
        for label, raw_path in sorted(files.items())
    ]
    artifacts.insert(0, _evidence_manifest_artifact(repo_id, manifest_path, manifest))
    check = _load_optional_artifact(manifest_path, manifest, "check_json")
    doctor = _load_optional_artifact(manifest_path, manifest, "doctor")
    registry = _load_optional_artifact(manifest_path, manifest, "registry")
    check_summary = check.get("summary") or {}
    doctor_summary = doctor.get("summary") or {}
    registry_summary = registry.get("summary") or {}
    return {
        "id": repo_id,
        "path": str(repo_root),
        "evidence_manifest": str(manifest_path),
        "config": str(manifest.get("config") or ""),
        "zone": str(manifest.get("zone") or ""),
        "policy_packs": list(manifest.get("policy_packs") or []),
        "artifacts": [artifact["label"] for artifact in artifacts],
        "policy": {
            "errors": int(check_summary.get("errors") or 0),
            "warnings": int(check_summary.get("warnings") or 0),
            "infos": int(check_summary.get("infos") or 0),
        },
        "registry": {
            "skills": int(registry_summary.get("unique_skills") or 0),
            "skill_refs": int(registry_summary.get("skill_refs") or 0),
            "duplicate_skill_ids": int(registry_summary.get("duplicate_skill_ids") or 0),
        },
        "readiness": {
            "score": int(doctor.get("score") or 0),
            "status": str(doctor.get("status") or "unknown"),
            "issues": int(doctor_summary.get("issues") or 0),
        },
        "ledger": {
            "bundle_hash": str((manifest.get("ledger") or {}).get("bundle_hash") or ""),
            "previous_bundle_hash": str(
                (manifest.get("ledger") or {}).get("previous_bundle_hash") or ""
            ),
            "artifact_hashes": len(artifact_hashes),
        },
        "_artifacts": artifacts,
    }


def _artifact_entry(
    repository_id: str,
    manifest_path: Path,
    label: str,
    raw_path: str,
    hash_record: dict[str, Any],
) -> dict[str, Any]:
    path = _resolve_artifact_path(manifest_path, raw_path)
    expected_hash = str(hash_record.get("value") or "")
    status = "ok"
    actual_hash = ""
    if not path.exists():
        status = "missing"
    else:
        actual_hash = _file_sha256(path)
        if expected_hash and actual_hash != expected_hash:
            status = "invalid"
    return {
        "repository_id": repository_id,
        "label": label,
        "kind": "evidence-artifact",
        "path": str(path),
        "hash": {
            "alg": str(hash_record.get("alg") or "SHA-256"),
            "value": expected_hash or actual_hash,
        },
        "actual_hash": actual_hash,
        "schema_kind": SCHEMA_KIND_BY_LABEL.get(label, ""),
        "required": label in {"check_json", "doctor", "instruction_manifest", "registry"},
        "status": status,
    }


def _evidence_manifest_artifact(
    repository_id: str,
    manifest_path: Path,
    manifest: dict[str, Any],
) -> dict[str, Any]:
    actual_hash = _file_sha256(manifest_path)
    return {
        "repository_id": repository_id,
        "label": "evidence_manifest",
        "kind": "evidence-manifest",
        "path": str(manifest_path),
        "hash": {"alg": "SHA-256", "value": actual_hash},
        "actual_hash": actual_hash,
        "schema_kind": "evidence",
        "required": True,
        "status": "invalid" if not (manifest.get("ledger") or {}).get("bundle_hash") else "ok",
    }


def _parse_manifest_spec(spec: str) -> tuple[str, Path]:
    if "=" in spec:
        repo_id, path = spec.split("=", 1)
        repo_id = repo_id.strip()
        if not repo_id:
            raise ValueError(f"Invalid manifest spec '{spec}': repository id is empty")
        return repo_id, Path(path.strip())
    return "", Path(spec)


def _manifest_sort_key(spec: str) -> tuple[str, str]:
    repo_id, path = _parse_manifest_spec(spec)
    return repo_id or Path(path).parent.parent.name, str(path)


def _resolve_artifact_path(manifest_path: Path, raw_path: str) -> Path:
    path = Path(str(raw_path))
    if path.is_absolute():
        return path
    candidates = [
        (Path.cwd() / path).resolve(),
        (manifest_path.parent / path).resolve(),
        (manifest_path.parent / path.name).resolve(),
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def _load_optional_artifact(
    manifest_path: Path,
    manifest: dict[str, Any],
    label: str,
) -> dict[str, Any]:
    raw_path = (manifest.get("files") or {}).get(label)
    if not raw_path:
        return {}
    path = _resolve_artifact_path(manifest_path, raw_path)
    return _load_json(path) if path.exists() else {}


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _index_artifact_hashes(artifacts: list[dict[str, Any]]) -> dict[str, dict[str, str]]:
    return {
        f"{artifact['repository_id']}:{artifact['label']}": {
            "alg": "SHA-256",
            "value": artifact["actual_hash"] or artifact["hash"]["value"],
            "path": artifact["path"],
        }
        for artifact in artifacts
    }


def _index_hash(index: dict[str, Any]) -> str:
    payload = json.loads(json.dumps(index, ensure_ascii=False, sort_keys=True))
    payload["ledger"]["index_hash"] = ""
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
