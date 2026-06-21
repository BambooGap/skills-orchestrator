"""Readiness doctor for team SkillOps projects."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from skills_orchestrator import __version__
from skills_orchestrator.checker import run_check
from skills_orchestrator.diagnostic import DiagnosticSeverity


def run_doctor(
    config_path: str,
    *,
    zone_id: str | None = None,
    policy_packs: tuple[str, ...] | list[str] = (),
    check_lock: str | None = None,
    agents_md: str = "AGENTS.md",
    profile: str = "adopter",
) -> dict[str, Any]:
    """Run local SkillOps readiness checks for a skills-orchestrator workspace."""
    if profile not in {"adopter", "maintainer"}:
        raise ValueError("doctor profile must be 'adopter' or 'maintainer'")
    report = run_check(
        config_path,
        zone_id=zone_id,
        policy_packs=policy_packs,
        check_lock=check_lock,
    )
    root = _workspace_root(config_path)
    issues = [_diagnostic_issue(diagnostic) for diagnostic in report.diagnostics]
    evidence = _evidence(root, check_lock=check_lock, agents_md=agents_md, profile=profile)
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
    label = "Maintainer readiness" if profile == "maintainer" else "Adopter readiness"
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
    root: Path, *, check_lock: str | None, agents_md: str, profile: str
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
