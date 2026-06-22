"""Dashboard snapshot generation from SkillOps evidence bundles."""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from glob import glob
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "skills-orchestrator.enterprise-dashboard-snapshot.v1"
ROLLUP_SCHEMA_VERSION = "skills-orchestrator.enterprise-dashboard-rollup.v1"


def build_dashboard_snapshot(
    evidence_dir: str | Path,
    *,
    repository: str | None = None,
    ref: str | None = None,
    commit: str | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    """Build an enterprise dashboard snapshot from an evidence bundle."""
    evidence_root = Path(evidence_dir).expanduser()
    if not evidence_root.is_absolute():
        evidence_root = (Path.cwd() / evidence_root).resolve()
    manifest_path = evidence_root / "evidence-manifest.json"
    manifest = _load_json(manifest_path)
    doctor = _load_json(_artifact_path(manifest_path, manifest, "doctor"))
    registry = _load_json(_artifact_path(manifest_path, manifest, "registry"))
    check = _load_json(_artifact_path(manifest_path, manifest, "check_json"))

    registry_summary = registry.get("summary") or {}
    check_summary = check.get("summary") or {}
    doctor_summary = doctor.get("summary") or {}
    ledger = manifest.get("ledger") or {}

    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": generated_at or _now_iso(),
        "repository": {
            "full_name": repository or os.environ.get("GITHUB_REPOSITORY") or "local/workspace",
            "ref": ref or os.environ.get("GITHUB_REF") or "",
            "commit": commit or os.environ.get("GITHUB_SHA") or "",
        },
        "readiness": {
            "score": int(doctor.get("score") or 0),
            "grade": str(doctor.get("status") or "unknown"),
            "profile": str(doctor.get("profile") or ""),
            "issues": int(doctor_summary.get("issues") or 0),
        },
        "registry": {
            "skills": int(registry_summary.get("unique_skills") or 0),
            "skill_refs": int(registry_summary.get("skill_refs") or 0),
            "owners": len(registry.get("owners") or {}),
            "duplicate_skill_ids": int(registry_summary.get("duplicate_skill_ids") or 0),
        },
        "policy": {
            "errors": int(check_summary.get("errors") or 0),
            "warnings": int(check_summary.get("warnings") or 0),
            "infos": int(check_summary.get("infos") or 0),
            "trace_entries": len(check.get("policy_trace") or []),
        },
        "artifacts": {
            "evidence_manifest": str(manifest_path),
            **{str(label): str(path) for label, path in (manifest.get("files") or {}).items()},
        },
        "ledger": {
            "bundle_hash": ledger.get("bundle_hash") or "",
            "previous_bundle_hash": ledger.get("previous_bundle_hash") or "",
            "artifact_hashes": len(ledger.get("artifact_hashes") or {}),
        },
    }


def format_dashboard_snapshot_json(snapshot: dict[str, Any]) -> str:
    """Return canonical pretty JSON for a dashboard snapshot."""
    return json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n"


def expand_snapshot_inputs(
    snapshots: tuple[str, ...] | list[str] = (),
    snapshot_globs: tuple[str, ...] | list[str] = (),
) -> list[Path]:
    """Resolve explicit snapshot paths and glob patterns in stable order."""
    paths: list[Path] = []
    for raw in snapshots:
        paths.append(Path(raw).expanduser())
    for pattern in snapshot_globs:
        paths.extend(Path(match).expanduser() for match in glob(pattern, recursive=True))
    resolved = sorted({str(path): path for path in paths}.values(), key=lambda item: str(item))
    if not resolved:
        raise ValueError("At least one --snapshot or --snapshot-glob input is required")
    return resolved


def build_dashboard_rollup(
    snapshot_paths: tuple[str, ...] | list[str] | list[Path],
    *,
    organization: str | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    """Build an organization-level dashboard rollup from dashboard snapshots."""
    snapshots = [_load_json(Path(path).expanduser()) for path in snapshot_paths]
    if not snapshots:
        raise ValueError("At least one dashboard snapshot is required")
    repositories = [
        _repository_summary(path, snapshot) for path, snapshot in zip(snapshot_paths, snapshots)
    ]
    repositories.sort(key=lambda item: (item["full_name"], item["ref"], item["source"]))
    scores = [int(item["readiness"]["score"]) for item in repositories]
    policy = _sum_section(repositories, "policy", ("errors", "warnings", "infos", "trace_entries"))
    registry = _sum_section(
        repositories,
        "registry",
        ("skills", "skill_refs", "owners", "duplicate_skill_ids"),
    )
    return {
        "schema_version": ROLLUP_SCHEMA_VERSION,
        "generated_at": generated_at or _now_iso(),
        "organization": organization or os.environ.get("GITHUB_REPOSITORY_OWNER") or "",
        "summary": {
            "repositories": len(repositories),
            "average_readiness_score": round(sum(scores) / len(scores), 2),
            "min_readiness_score": min(scores),
            "max_readiness_score": max(scores),
            "policy_errors": policy["errors"],
            "policy_warnings": policy["warnings"],
            "policy_infos": policy["infos"],
            "registry_skills": registry["skills"],
            "registry_owners": registry["owners"],
            "duplicate_skill_ids": registry["duplicate_skill_ids"],
        },
        "repositories": repositories,
    }


def format_dashboard_rollup_json(rollup: dict[str, Any]) -> str:
    """Return canonical pretty JSON for a dashboard rollup."""
    return json.dumps(rollup, ensure_ascii=False, indent=2) + "\n"


def _artifact_path(
    manifest_path: Path,
    manifest: dict[str, Any],
    label: str,
) -> Path:
    files = manifest.get("files") or {}
    try:
        raw = files[label]
    except KeyError as exc:
        raise ValueError(f"Evidence manifest is missing artifact '{label}'") from exc
    path = Path(str(raw))
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


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _repository_summary(path: str | Path, snapshot: dict[str, Any]) -> dict[str, Any]:
    repository = snapshot.get("repository") or {}
    return {
        "source": str(path),
        "full_name": str(repository.get("full_name") or ""),
        "ref": str(repository.get("ref") or ""),
        "commit": str(repository.get("commit") or ""),
        "readiness": {
            "score": int((snapshot.get("readiness") or {}).get("score") or 0),
            "grade": str((snapshot.get("readiness") or {}).get("grade") or "unknown"),
            "issues": int((snapshot.get("readiness") or {}).get("issues") or 0),
        },
        "policy": {
            "errors": int((snapshot.get("policy") or {}).get("errors") or 0),
            "warnings": int((snapshot.get("policy") or {}).get("warnings") or 0),
            "infos": int((snapshot.get("policy") or {}).get("infos") or 0),
            "trace_entries": int((snapshot.get("policy") or {}).get("trace_entries") or 0),
        },
        "registry": {
            "skills": int((snapshot.get("registry") or {}).get("skills") or 0),
            "skill_refs": int((snapshot.get("registry") or {}).get("skill_refs") or 0),
            "owners": int((snapshot.get("registry") or {}).get("owners") or 0),
            "duplicate_skill_ids": int(
                (snapshot.get("registry") or {}).get("duplicate_skill_ids") or 0
            ),
        },
        "ledger": {
            "bundle_hash": str((snapshot.get("ledger") or {}).get("bundle_hash") or ""),
            "previous_bundle_hash": str(
                (snapshot.get("ledger") or {}).get("previous_bundle_hash") or ""
            ),
        },
    }


def _sum_section(
    repositories: list[dict[str, Any]],
    section: str,
    keys: tuple[str, ...],
) -> dict[str, int]:
    return {
        key: sum(int((repository.get(section) or {}).get(key) or 0) for repository in repositories)
        for key in keys
    }


def _now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
