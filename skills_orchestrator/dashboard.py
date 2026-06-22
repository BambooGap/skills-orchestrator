"""Dashboard snapshot generation from SkillOps evidence bundles."""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "skills-orchestrator.enterprise-dashboard-snapshot.v1"


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


def _now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
