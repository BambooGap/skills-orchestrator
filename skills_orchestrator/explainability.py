"""CI-level explainability artifacts for SkillOps checks."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from skills_orchestrator import __version__
from skills_orchestrator.diagnostic import DiagnosticReport

SCHEMA_VERSION = "skills-orchestrator.ci-explainability.v1"


def build_ci_explainability(
    report: DiagnosticReport,
    *,
    config_path: str | None = None,
    fail_on: str = "error",
    generated_at: str | None = None,
) -> dict[str, Any]:
    """Build a machine-readable CI failure explanation from a check report."""
    summary = report.summary()
    payload = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": generated_at or _now_iso(),
        "tool": {"name": "skills-orchestrator", "version": __version__},
        "source": {"kind": "check", "config": config_path or ""},
        "status": _status(summary),
        "summary": _trace_summary([item.to_dict() for item in report.policy_trace], summary),
        "ci_decision": _ci_decision(summary, fail_on),
        "decisions": [_decision_from_trace(item.to_dict()) for item in report.policy_trace],
    }
    payload["failure_explainability"] = [
        _failure_explanation(item) for item in payload["decisions"] if item["outcome"] == "fail"
    ]
    return payload


def build_ci_explainability_from_check_payload(
    check_payload: dict[str, Any],
    *,
    config_path: str | None = None,
    fail_on: str = "error",
    generated_at: str | None = None,
) -> dict[str, Any]:
    """Build CI explainability from an existing check --format json payload."""
    summary = dict(check_payload.get("summary") or {})
    traces = list(check_payload.get("policy_trace") or [])
    source = {"kind": "check", "config": config_path or ""}
    source["check_schema_version"] = check_payload.get("schema_version", "")
    payload = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": generated_at or _now_iso(),
        "tool": check_payload.get("tool", {"name": "skills-orchestrator", "version": __version__}),
        "source": source,
        "status": _status(summary),
        "summary": _trace_summary(traces, summary),
        "ci_decision": _ci_decision(summary, fail_on),
        "decisions": [_decision_from_trace(item) for item in traces],
    }
    payload["failure_explainability"] = [
        _failure_explanation(item) for item in payload["decisions"] if item["outcome"] == "fail"
    ]
    return payload


def format_ci_explainability_json(payload: dict[str, Any]) -> str:
    """Serialize CI explainability JSON deterministically enough for CI artifacts."""
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def _trace_summary(traces: list[dict[str, Any]], check_summary: dict[str, Any]) -> dict[str, int]:
    passed = sum(1 for item in traces if item.get("outcome") == "pass")
    failed = sum(1 for item in traces if item.get("outcome") == "fail")
    skipped = sum(1 for item in traces if item.get("outcome") == "skip")
    return {
        "total_decisions": len(traces),
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "diagnostics": int(check_summary.get("total", 0) or 0),
        "errors": int(check_summary.get("errors", 0) or 0),
        "warnings": int(check_summary.get("warnings", 0) or 0),
        "infos": int(check_summary.get("infos", 0) or 0),
        "skills": int(check_summary.get("skills", 0) or 0),
        "zones": int(check_summary.get("zones", 0) or 0),
        "combos": int(check_summary.get("combos", 0) or 0),
    }


def _decision_from_trace(trace: dict[str, Any]) -> dict[str, Any]:
    diagnostic = trace.get("diagnostic") or {}
    severity = diagnostic.get("severity")
    suggested_fix = diagnostic.get("suggested_fix")
    return {
        "rule_id": trace.get("rule_id") or "",
        "outcome": trace.get("outcome") or "skip",
        "severity": severity,
        "scope": trace.get("scope") or "unknown",
        "policy_pack": trace.get("policy_pack"),
        "reason": trace.get("reason") or "",
        "location": {
            "file": trace.get("file"),
            "line": trace.get("line"),
            "skill_id": trace.get("skill_id"),
        },
        "input_facts": trace.get("input_facts") or {},
        "suggested_fix": suggested_fix,
        "ci_effect": _ci_effect(trace.get("outcome"), severity),
        "diagnostic": diagnostic or None,
        "metadata": trace.get("metadata") or {},
    }


def _failure_explanation(decision: dict[str, Any]) -> dict[str, Any]:
    return {
        "rule_id": decision["rule_id"],
        "severity": decision.get("severity"),
        "scope": decision["scope"],
        "policy_pack": decision.get("policy_pack"),
        "message": decision["reason"],
        "location": decision["location"],
        "suggested_fix": decision.get("suggested_fix"),
        "ci_effect": decision["ci_effect"],
    }


def _ci_decision(summary: dict[str, Any], fail_on: str) -> dict[str, Any]:
    status = _status(summary)
    blocking = _blocking(summary, fail_on)
    if blocking:
        reason = (
            f"check has {summary.get('errors', 0)} errors and {summary.get('warnings', 0)} warnings"
        )
    elif status == "warn":
        reason = "warnings found; default CI gate is advisory unless fail-on=warning"
    else:
        reason = "no blocking SkillOps diagnostics"
    return {
        "outcome": status,
        "blocking": blocking,
        "fail_on": fail_on,
        "reason": reason,
    }


def _status(summary: dict[str, Any]) -> str:
    if int(summary.get("errors", 0) or 0) > 0:
        return "fail"
    if int(summary.get("warnings", 0) or 0) > 0:
        return "warn"
    return "pass"


def _blocking(summary: dict[str, Any], fail_on: str) -> bool:
    if fail_on == "never":
        return False
    if int(summary.get("errors", 0) or 0) > 0:
        return fail_on in {"error", "warning"}
    if int(summary.get("warnings", 0) or 0) > 0:
        return fail_on == "warning"
    return False


def _ci_effect(outcome: object, severity: object) -> str:
    if outcome != "fail":
        return "passed"
    if severity == "error":
        return "blocking-by-default"
    if severity == "warning":
        return "advisory-by-default"
    return "informational"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
