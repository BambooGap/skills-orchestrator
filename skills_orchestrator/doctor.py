"""Readiness doctor for team SkillOps projects."""

from __future__ import annotations

import re
from json import JSONDecodeError
from pathlib import Path
from typing import Any

from skills_orchestrator import __version__
from skills_orchestrator.checker import run_check
from skills_orchestrator.diagnostic import DiagnosticSeverity
from skills_orchestrator.schema_validation import validate_document


def run_doctor(
    config_path: str,
    *,
    zone_id: str | None = None,
    policy_packs: tuple[str, ...] | list[str] = (),
    check_lock: str | None = None,
    agents_md: str = "AGENTS.md",
    profile: str = "adopter",
    evidence_dir: str = "evidence",
) -> dict[str, Any]:
    """Run local SkillOps readiness checks for a skills-orchestrator workspace."""
    if profile not in {"adopter", "maintainer", "enterprise"}:
        raise ValueError("doctor profile must be 'adopter', 'maintainer', or 'enterprise'")
    report = run_check(
        config_path,
        zone_id=zone_id,
        policy_packs=policy_packs,
        check_lock=check_lock,
    )
    root = _workspace_root(config_path)
    issues = [_diagnostic_issue(diagnostic) for diagnostic in report.diagnostics]
    evidence = _evidence(
        root,
        check_lock=check_lock,
        agents_md=agents_md,
        profile=profile,
        evidence_dir=evidence_dir,
    )
    issues.extend(evidence["issues"])
    score = _score(issues)
    return {
        "schema_version": "skills-orchestrator.doctor.v1",
        "tool": {"name": "skills-orchestrator", "version": __version__},
        "profile": profile,
        "zone": zone_id or "default",
        "score": score,
        "status": _status(score, issues, profile=profile),
        "summary": {
            "skills": report.total_skills,
            "zones": report.zones,
            "combos": report.combos,
            "issues": len(issues),
            "errors": sum(1 for issue in issues if issue["severity"] == "error"),
            "warnings": sum(1 for issue in issues if issue["severity"] == "warning"),
            "infos": sum(1 for issue in issues if issue["severity"] == "info"),
        },
        "evidence": evidence["artifacts"],
        "issues": issues,
    }


def format_doctor_text(payload: dict[str, Any]) -> str:
    """Render a doctor payload for terminal use."""
    profile = payload.get("profile", "adopter")
    labels = {
        "adopter": "Adopter readiness",
        "maintainer": "Maintainer readiness",
        "enterprise": "Enterprise readiness",
    }
    label = labels.get(profile, f"{profile.title()} readiness")
    lines = [
        f"{label}: {payload['score']}/100 ({payload['status']})",
        (
            "Summary: "
            f"{payload['summary']['skills']} skills, "
            f"{payload['summary']['errors']} errors, "
            f"{payload['summary']['warnings']} warnings, "
            f"{payload['summary']['infos']} infos"
        ),
        "",
        "Evidence:",
    ]
    for key, value in payload["evidence"].items():
        marker = "OK" if value["present"] else "MISSING"
        detail = f" - {value['detail']}" if value.get("detail") else ""
        lines.append(f"  [{marker}] {key}: {value['path']}{detail}")

    if payload["issues"]:
        lines.append("")
        lines.append("Issues:")
        for issue in payload["issues"]:
            location = f" ({issue['file']}:{issue['line']})" if issue.get("file") else ""
            lines.append(
                f"  [{issue['severity'].upper()}] {issue['id']}: {issue['message']}{location}"
            )
            if issue.get("suggested_fix"):
                lines.append(f"    fix: {issue['suggested_fix']}")
    else:
        lines.append("")
        lines.append("Issues: none")

    return "\n".join(lines) + "\n"


def _workspace_root(config_path: str) -> Path:
    config = Path(config_path).expanduser()
    if not config.is_absolute():
        config = (Path.cwd() / config).resolve()
    else:
        config = config.resolve()
    return config.parent.parent if config.parent.name == "config" else config.parent


def _diagnostic_issue(diagnostic) -> dict[str, Any]:
    return {
        "id": diagnostic.rule_id,
        "severity": diagnostic.severity.value,
        "message": diagnostic.message,
        "file": diagnostic.file,
        "line": diagnostic.line,
        "suggested_fix": diagnostic.suggested_fix,
        "metadata": diagnostic.metadata,
    }


def _evidence(
    root: Path,
    *,
    check_lock: str | None,
    agents_md: str,
    profile: str,
    evidence_dir: str,
) -> dict[str, Any]:
    artifacts: dict[str, dict[str, Any]] = {}
    issues: list[dict[str, Any]] = []

    workflow_path, workflow_detail = _skillops_workflow(root)
    _record_artifact(artifacts, "ci_workflow", workflow_path, detail=workflow_detail)
    if not workflow_path.exists():
        issues.append(
            _artifact_issue(
                "DOCTOR_CI_WORKFLOW",
                "warning",
                f"Missing SkillOps CI workflow artifact: {workflow_path}",
                "Add a workflow that runs skills-orchestrator check in CI.",
                str(workflow_path),
            )
        )

    if profile == "maintainer":
        _maintainer_release_evidence(root, artifacts, issues)

    lock_path = Path(check_lock) if check_lock else root / "skills.lock.json"
    _record_artifact(artifacts, "skills_lock", lock_path)
    if not lock_path.exists():
        issues.append(
            _artifact_issue(
                "DOCTOR_LOCK",
                "warning",
                f"Missing skills lock artifact: {lock_path}",
                "Run skills-orchestrator build --lock after reviewing skill changes.",
                str(lock_path),
            )
        )

    agents_path = Path(agents_md)
    if not agents_path.is_absolute():
        agents_path = root / agents_path
    detail = _agents_detail(agents_path)
    _record_artifact(artifacts, "agents_md", agents_path, detail=detail)
    if not agents_path.exists():
        issues.append(
            _artifact_issue(
                "DOCTOR_AGENTS",
                "warning",
                f"Missing generated AGENTS.md artifact: {agents_path}",
                "Run skills-orchestrator build --output AGENTS.md.",
                str(agents_path),
            )
        )
    elif detail and detail != f"v{__version__}":
        issues.append(
            _artifact_issue(
                "DOCTOR_AGENTS_STALE",
                "warning",
                f"AGENTS.md was generated by {detail}, but package version is v{__version__}.",
                "Regenerate AGENTS.md so team bootstrap guidance matches the current tool.",
                str(agents_path),
            )
        )

    if profile == "enterprise":
        _enterprise_evidence(root, evidence_dir, artifacts, issues)

    return {"artifacts": artifacts, "issues": issues}


def _skillops_workflow(root: Path) -> tuple[Path, str]:
    workflows_dir = root / ".github" / "workflows"
    named_candidates = [
        workflows_dir / "skills-orchestrator.yml",
        workflows_dir / "skillops.yml",
    ]
    for path in named_candidates:
        if path.exists():
            return path, "detected SkillOps workflow"

    generic_ci_candidates = [workflows_dir / "ci.yml", workflows_dir / "ci.yaml"]
    for path in generic_ci_candidates:
        if path.exists() and _workflow_references_skillops(path):
            return path, "detected Skills Orchestrator workflow by content"

    if workflows_dir.is_dir():
        for path in sorted([*workflows_dir.glob("*.yml"), *workflows_dir.glob("*.yaml")]):
            if _workflow_references_skillops(path):
                return path, "detected Skills Orchestrator workflow by content"

    expected = workflows_dir / "skills-orchestrator.yml"
    return expected, "expected skills-orchestrator.yml, skillops.yml, ci.yml, or ci.yaml"


def _workflow_references_skillops(path: Path) -> bool:
    content = path.read_text(encoding="utf-8", errors="replace")[:20000]
    return "skills-orchestrator" in content or "BambooGap/skills-orchestrator" in content


def _maintainer_release_evidence(
    root: Path, artifacts: dict[str, dict[str, Any]], issues: list[dict[str, Any]]
) -> None:
    for name, path, fix in (
        (
            "github_action",
            root / "action.yml",
            "Add or document the GitHub Action release surface.",
        ),
        (
            "dockerfile",
            root / "Dockerfile",
            "Add a Dockerfile for containerized CLI release and smoke tests.",
        ),
        (
            "test_report",
            root / "reports" / f"TEST_REPORT_v{__version__}.md",
            "Write a versioned test report for this release.",
        ),
    ):
        _record_artifact(artifacts, name, path)
        if not path.exists():
            issues.append(
                _artifact_issue(
                    f"DOCTOR_{name.upper()}",
                    "warning",
                    f"Missing maintainer release artifact: {path}",
                    fix,
                    str(path),
                )
            )


def _enterprise_evidence(
    root: Path,
    evidence_dir: str,
    artifacts: dict[str, dict[str, Any]],
    issues: list[dict[str, Any]],
) -> None:
    evidence_root = Path(evidence_dir)
    if not evidence_root.is_absolute():
        evidence_root = root / evidence_root

    manifest_path = evidence_root / "evidence-manifest.json"
    detail = _schema_detail("evidence", manifest_path)
    _record_artifact(artifacts, "evidence_manifest", manifest_path, detail=detail)
    if not manifest_path.exists():
        issues.append(
            _artifact_issue(
                "DOCTOR_EVIDENCE_MANIFEST",
                "warning",
                f"Missing evidence manifest artifact: {manifest_path}",
                "Run skills-orchestrator evidence export before enterprise readiness checks.",
                str(manifest_path),
            )
        )
        return
    if not detail.startswith("schema valid"):
        issues.append(
            _artifact_issue(
                "DOCTOR_EVIDENCE_SCHEMA",
                "error",
                f"Evidence manifest failed schema validation: {detail}",
                "Regenerate the evidence bundle with the current skills-orchestrator version.",
                str(manifest_path),
            )
        )
        return

    try:
        import json

        bundle = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, JSONDecodeError) as exc:
        issues.append(
            _artifact_issue(
                "DOCTOR_EVIDENCE_READ",
                "error",
                f"Evidence manifest could not be read: {exc}",
                "Regenerate the evidence bundle.",
                str(manifest_path),
            )
        )
        return

    expected_schema = {
        "check_json": "check",
        "instruction_manifest": "manifest",
        "opa_input": "policy-opa-input",
        "doctor": "doctor",
        "registry": "registry",
    }
    files = bundle.get("files") or {}
    for label, schema_kind in expected_schema.items():
        path_text = files.get(label)
        path = (
            _resolve_evidence_artifact_path(path_text, root=root, manifest_path=manifest_path)
            if path_text
            else evidence_root / f"{label}.missing"
        )
        detail = _schema_detail(schema_kind, path)
        _record_artifact(artifacts, f"evidence_{label}", path, detail=detail)
        if not path_text or not path.exists():
            issues.append(
                _artifact_issue(
                    f"DOCTOR_EVIDENCE_{label.upper()}",
                    "warning",
                    f"Missing evidence artifact: {label}",
                    "Regenerate the evidence bundle and keep all referenced files.",
                    str(path),
                )
            )
        elif not detail.startswith("schema valid"):
            issues.append(
                _artifact_issue(
                    f"DOCTOR_EVIDENCE_{label.upper()}_SCHEMA",
                    "error",
                    f"Evidence artifact failed schema validation: {label} - {detail}",
                    "Regenerate the evidence bundle with the current skills-orchestrator version.",
                    str(path),
                )
            )

    optional_artifacts = (
        ("adapter_inspect", evidence_root / "adapter-inspect.json", "adapter-inspect"),
        ("package_sbom", evidence_root / "package-sbom.cdx.json", "supply-chain-sbom"),
    )
    for label, path, schema_kind in optional_artifacts:
        detail = _schema_detail(schema_kind, path) if path.exists() else "recommended"
        _record_artifact(artifacts, label, path, detail=detail)
        if not path.exists():
            issues.append(
                _artifact_issue(
                    f"DOCTOR_{label.upper()}",
                    "info",
                    f"Recommended enterprise artifact is missing: {path}",
                    "Generate this artifact when piloting organization-wide SkillOps evidence.",
                    str(path),
                )
            )
        elif not detail.startswith("schema valid"):
            issues.append(
                _artifact_issue(
                    f"DOCTOR_{label.upper()}_SCHEMA",
                    "warning",
                    f"Recommended enterprise artifact failed schema validation: {detail}",
                    "Regenerate the artifact with the current skills-orchestrator version.",
                    str(path),
                )
            )


def _schema_detail(kind: str, path: Path) -> str:
    if not path.exists():
        return "missing"
    try:
        result = validate_document(kind, str(path))
    except Exception as exc:
        return f"schema error: {exc}"
    if result.valid:
        return "schema valid"
    return "schema invalid: " + "; ".join(
        f"{issue.path}: {issue.message}" for issue in result.errors[:3]
            )


def _resolve_evidence_artifact_path(path_text: str, *, root: Path, manifest_path: Path) -> Path:
    path = Path(path_text)
    if path.is_absolute():
        return path
    candidates = [
        (Path.cwd() / path).resolve(),
        (root / path).resolve(),
        (manifest_path.parent / path).resolve(),
        (manifest_path.parent / path.name).resolve(),
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def _record_artifact(
    artifacts: dict[str, dict[str, Any]], name: str, path: Path, *, detail: str = ""
) -> None:
    artifacts[name] = {
        "path": str(path),
        "present": path.exists(),
        "detail": detail,
    }


def _agents_detail(path: Path) -> str:
    if not path.exists():
        return ""
    first_line = path.read_text(encoding="utf-8", errors="replace").splitlines()[0:1]
    if not first_line:
        return ""
    match = re.search(r"Skills Orchestrator (v[0-9][^ |]*)", first_line[0])
    return match.group(1) if match else ""


def _artifact_issue(
    issue_id: str,
    severity: str,
    message: str,
    suggested_fix: str,
    file_path: str,
) -> dict[str, Any]:
    return {
        "id": issue_id,
        "severity": severity,
        "message": message,
        "file": file_path,
        "line": 1,
        "suggested_fix": suggested_fix,
        "metadata": {},
    }


def _score(issues: list[dict[str, Any]]) -> int:
    score = 100
    for issue in issues:
        severity = issue["severity"]
        if severity == DiagnosticSeverity.ERROR.value:
            score -= 20
        elif severity == DiagnosticSeverity.WARNING.value:
            score -= 5
        else:
            score -= 1
    return max(score, 0)


def _status(score: int, issues: list[dict[str, Any]], *, profile: str) -> str:
    if any(issue["severity"] == "error" for issue in issues):
        return "blocked"
    if score < 70:
        return "risky"
    if score < 85:
        return f"{profile}-ready-with-caveats"
    return "strong"
