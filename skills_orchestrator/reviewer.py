"""Reviewer-facing SkillOps summary artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from skills_orchestrator.explainability import build_ci_explainability_from_check_payload

SCHEMA_VERSION = "skills-orchestrator.reviewer-summary.v1"


def build_reviewer_summary(
    *,
    check_json: str | Path | None = None,
    registry_diff_json: str | Path | None = None,
    registry_diff_markdown: str | Path | None = None,
    registry_graph: str | Path | None = None,
    evidence_manifest: str | Path | None = None,
) -> dict[str, Any]:
    """Build a compact reviewer summary from existing SkillOps artifacts."""
    check_payload = _load_optional_json(check_json)
    diff_payload = _load_optional_json(registry_diff_json)
    graph_payload = _load_optional_json(registry_graph)
    evidence_payload = _load_optional_json(evidence_manifest)

    payload = {
        "schema_version": SCHEMA_VERSION,
        "inputs": {
            "check_json": _path_text(check_json),
            "registry_diff_json": _path_text(registry_diff_json),
            "registry_diff_markdown": _path_text(registry_diff_markdown),
            "registry_graph": _path_text(registry_graph),
            "evidence_manifest": _path_text(evidence_manifest),
        },
        "check": _check_summary(check_payload),
        "ci_explainability": _ci_explainability_summary(check_payload),
        "policy_trace": _policy_trace_summary(check_payload),
        "registry_diff": _registry_diff_summary(diff_payload),
        "registry_graph": _registry_graph_summary(graph_payload),
        "evidence": _evidence_summary(evidence_payload),
    }
    return payload


def render_reviewer_summary_markdown(summary: dict[str, Any]) -> str:
    """Render reviewer summary JSON as a stable Markdown artifact."""
    check = summary["check"]
    explainability = summary["ci_explainability"]
    trace = summary["policy_trace"]
    diff = summary["registry_diff"]
    graph = summary["registry_graph"]
    evidence = summary["evidence"]

    lines = [
        "# SkillOps Reviewer Summary",
        "",
        "## Decision Inputs",
        "",
        "| Area | Status | Detail |",
        "| --- | --- | --- |",
        f"| Check | {_status(check['status'])} | {_check_detail(check)} |",
        f"| CI explainability | {_status(explainability['status'])} | "
        f"{_ci_explainability_detail(explainability)} |",
        f"| Policy trace | {_status(trace['status'])} | {_trace_detail(trace)} |",
        f"| Registry diff | {_status(diff['status'])} | {_diff_detail(diff)} |",
        f"| Registry graph | {_status(graph['status'])} | {_graph_detail(graph)} |",
        f"| Evidence ledger | {_status(evidence['status'])} | {_evidence_detail(evidence)} |",
        "",
    ]

    diagnostics = check.get("top_diagnostics", [])
    if diagnostics:
        lines.extend(["## Top Diagnostics", ""])
        lines.append("| Rule | Severity | Location | Message |")
        lines.append("| --- | --- | --- | --- |")
        for item in diagnostics:
            location = item.get("file") or ""
            if item.get("line"):
                location = f"{location}:{item['line']}" if location else str(item["line"])
            lines.append(
                "| "
                f"{_code(item.get('rule_id') or 'unknown')} | "
                f"{_escape(item.get('severity') or '')} | "
                f"{_code(location) if location else ''} | "
                f"{_escape(item.get('message') or '')} |"
            )
        lines.append("")

    failures = explainability.get("failures", [])
    if failures:
        lines.extend(["## CI Failure Explainability", ""])
        lines.append("| Rule | Effect | Location | Reason | Suggested fix |")
        lines.append("| --- | --- | --- | --- | --- |")
        for item in failures:
            location_data = item.get("location") or {}
            location = location_data.get("file") or ""
            if location_data.get("line"):
                location = (
                    f"{location}:{location_data['line']}"
                    if location
                    else str(location_data["line"])
                )
            lines.append(
                "| "
                f"{_code(item.get('rule_id') or 'unknown')} | "
                f"{_escape(item.get('ci_effect') or '')} | "
                f"{_code(location) if location else ''} | "
                f"{_escape(item.get('message') or '')} | "
                f"{_escape(item.get('suggested_fix') or '')} |"
            )
        lines.append("")

    changed = diff.get("changed_skills", [])
    if changed:
        lines.extend(["## Changed Skills", ""])
        lines.append("| Skill | Owner | Path | Changes |")
        lines.append("| --- | --- | --- | --- |")
        for item in changed:
            lines.append(
                "| "
                f"{_code(item.get('id') or '')} | "
                f"{_code(item.get('owner') or '')} | "
                f"{_code(item.get('path') or '')} | "
                f"{_escape(', '.join(item.get('changes', [])))} |"
            )
        lines.append("")

    if evidence.get("bundle_hash"):
        lines.extend(
            [
                "## Evidence Ledger",
                "",
                f"- Bundle hash: `{evidence['bundle_hash']}`",
                f"- Previous bundle hash: `{evidence.get('previous_bundle_hash') or '(none)'}`",
                f"- Artifact hashes: {evidence.get('artifact_hashes', 0)}",
                "",
            ]
        )

    registry_diff_markdown = summary.get("inputs", {}).get("registry_diff_markdown")
    if registry_diff_markdown:
        lines.extend(
            [
                "## Full Registry Diff",
                "",
                f"See `{registry_diff_markdown}` for the full reviewer diff.",
                "",
            ]
        )

    lines.extend(
        [
            "---",
            "Generated by `skills-orchestrator reviewer summary`. "
            "This summarizes CI artifacts, not agent runtime reasoning.",
            "",
        ]
    )
    return "\n".join(lines)


def format_reviewer_summary_json(summary: dict[str, Any]) -> str:
    """Return canonical pretty JSON for reviewer summary."""
    return json.dumps(summary, ensure_ascii=False, indent=2) + "\n"


def _load_optional_json(path: str | Path | None) -> dict[str, Any] | None:
    if not path:
        return None
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _path_text(path: str | Path | None) -> str:
    return str(path) if path else ""


def _check_summary(payload: dict[str, Any] | None) -> dict[str, Any]:
    if not payload:
        return {
            "status": "missing",
            "errors": 0,
            "warnings": 0,
            "infos": 0,
            "total": 0,
            "top_diagnostics": [],
        }
    summary = payload.get("summary") or {}
    diagnostics = payload.get("diagnostics") or []
    errors = int(summary.get("errors") or 0)
    warnings = int(summary.get("warnings") or 0)
    status = "fail" if errors else "warn" if warnings else "pass"
    return {
        "status": status,
        "errors": errors,
        "warnings": warnings,
        "infos": int(summary.get("infos") or 0),
        "total": int(summary.get("total") or len(diagnostics)),
        "top_diagnostics": diagnostics[:10],
    }


def _policy_trace_summary(payload: dict[str, Any] | None) -> dict[str, Any]:
    if not payload:
        return {"status": "missing", "total": 0, "outcomes": {}, "failed_rules": []}
    trace = payload.get("policy_trace") or []
    outcomes: dict[str, int] = {}
    failed_rules: list[str] = []
    for item in trace:
        outcome = str(item.get("outcome") or "unknown")
        outcomes[outcome] = outcomes.get(outcome, 0) + 1
        if outcome not in {"pass", "skip"}:
            rule = str(item.get("rule_id") or "unknown")
            if rule not in failed_rules:
                failed_rules.append(rule)
    status = "pass" if trace and not failed_rules else "warn" if trace else "missing"
    return {
        "status": status,
        "total": len(trace),
        "outcomes": outcomes,
        "failed_rules": failed_rules[:20],
    }


def _ci_explainability_summary(payload: dict[str, Any] | None) -> dict[str, Any]:
    if not payload:
        return {
            "status": "missing",
            "outcome": "missing",
            "blocking": False,
            "reason": "No check JSON artifact.",
            "failures": [],
        }
    explainability = build_ci_explainability_from_check_payload(payload)
    decision = explainability["ci_decision"]
    return {
        "status": explainability["status"],
        "outcome": decision["outcome"],
        "blocking": bool(decision["blocking"]),
        "reason": decision["reason"],
        "failures": explainability["failure_explainability"][:10],
    }


def _registry_diff_summary(payload: dict[str, Any] | None) -> dict[str, Any]:
    if not payload:
        return {
            "status": "missing",
            "added": 0,
            "removed": 0,
            "changed": 0,
            "duplicate_id_changes": 0,
            "changed_skills": [],
        }
    summary = payload.get("summary") or {}
    changed_skills = [_changed_skill_summary(item) for item in payload.get("changed", [])[:20]]
    total_changes = sum(
        int(summary.get(key) or 0)
        for key in ("added", "removed", "changed", "duplicate_id_changes")
    )
    return {
        "status": "pass" if total_changes == 0 else "review",
        "added": int(summary.get("added") or 0),
        "removed": int(summary.get("removed") or 0),
        "changed": int(summary.get("changed") or 0),
        "duplicate_id_changes": int(summary.get("duplicate_id_changes") or 0),
        "changed_skills": changed_skills,
    }


def _changed_skill_summary(item: dict[str, Any]) -> dict[str, Any]:
    skill = item.get("skill") or {}
    governance = skill.get("governance") or {}
    changes = item.get("changes") or {}
    return {
        "id": item.get("id") or skill.get("id") or "",
        "owner": governance.get("owner") or "",
        "path": skill.get("path") or "",
        "changes": sorted(changes),
    }


def _registry_graph_summary(payload: dict[str, Any] | None) -> dict[str, Any]:
    if not payload:
        return {"status": "missing", "nodes": 0, "edges": 0, "node_types": {}}
    summary = payload.get("summary") or {}
    node_types: dict[str, int] = {}
    for node in payload.get("nodes") or []:
        node_type = str(node.get("type") or "unknown")
        node_types[node_type] = node_types.get(node_type, 0) + 1
    return {
        "status": "pass",
        "nodes": int(summary.get("nodes") or len(payload.get("nodes") or [])),
        "edges": int(summary.get("edges") or len(payload.get("edges") or [])),
        "node_types": node_types,
    }


def _evidence_summary(payload: dict[str, Any] | None) -> dict[str, Any]:
    if not payload:
        return {
            "status": "missing",
            "bundle_hash": "",
            "previous_bundle_hash": "",
            "artifact_hashes": 0,
        }
    ledger = payload.get("ledger") or {}
    artifact_hashes = ledger.get("artifact_hashes") or {}
    return {
        "status": "pass" if ledger.get("bundle_hash") else "warn",
        "bundle_hash": ledger.get("bundle_hash") or "",
        "previous_bundle_hash": ledger.get("previous_bundle_hash") or "",
        "artifact_hashes": len(artifact_hashes),
    }


def _check_detail(check: dict[str, Any]) -> str:
    if check["status"] == "missing":
        return "No check JSON artifact."
    return f"{check['errors']} errors, {check['warnings']} warnings, {check['infos']} infos."


def _trace_detail(trace: dict[str, Any]) -> str:
    if trace["status"] == "missing":
        return "No policy trace artifact."
    outcomes = ", ".join(f"{key}={value}" for key, value in sorted(trace["outcomes"].items()))
    return f"{trace['total']} trace entries ({outcomes or 'no outcomes'})."


def _ci_explainability_detail(explainability: dict[str, Any]) -> str:
    if explainability["status"] == "missing":
        return "No CI explainability artifact."
    blocking = "blocking" if explainability["blocking"] else "advisory"
    failures = len(explainability.get("failures", []))
    return f"{explainability['outcome']} decision, {blocking}, {failures} failure explanations."


def _diff_detail(diff: dict[str, Any]) -> str:
    if diff["status"] == "missing":
        return "No registry diff JSON artifact."
    return (
        f"added={diff['added']}, removed={diff['removed']}, "
        f"changed={diff['changed']}, duplicate-id={diff['duplicate_id_changes']}."
    )


def _graph_detail(graph: dict[str, Any]) -> str:
    if graph["status"] == "missing":
        return "No registry graph artifact."
    return f"{graph['nodes']} nodes, {graph['edges']} edges."


def _evidence_detail(evidence: dict[str, Any]) -> str:
    if evidence["status"] == "missing":
        return "No evidence manifest artifact."
    return f"bundle={evidence['bundle_hash'][:12]}, artifacts={evidence['artifact_hashes']}."


def _status(status: str) -> str:
    labels = {
        "pass": "pass",
        "warn": "warn",
        "fail": "fail",
        "review": "review",
        "missing": "missing",
    }
    return labels.get(status, status)


def _escape(value: str) -> str:
    return (
        value.replace("&", "&amp;").replace("|", "&#124;").replace("<", "&lt;").replace(">", "&gt;")
    )


def _code(value: str) -> str:
    return f"<code>{_escape(value)}</code>" if value else ""
