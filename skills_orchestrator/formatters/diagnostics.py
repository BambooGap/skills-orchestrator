"""Diagnostic output formatters."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from skills_orchestrator import __version__
from skills_orchestrator.diagnostic import Diagnostic, DiagnosticReport, DiagnosticSeverity, RULES


def format_diagnostics_json(report: DiagnosticReport) -> str:
    payload = {
        "schema_version": "1.0",
        "generated_at": _now_iso(),
        "tool": {"name": "skills-orchestrator", "version": __version__},
        "summary": report.summary(),
        "diagnostics": [diagnostic.to_dict() for diagnostic in report.diagnostics],
    }
    return json.dumps(payload, indent=2, ensure_ascii=False) + "\n"


def format_diagnostics_sarif(report: DiagnosticReport) -> str:
    rules = list(RULES.values())
    rule_indexes = {rule.rule_id: index for index, rule in enumerate(rules)}
    payload: dict[str, Any] = {
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "skills-orchestrator",
                        "version": __version__,
                        "informationUri": "https://github.com/BambooGap/skills-orchestrator",
                        "rules": [
                            {
                                "id": rule.rule_id,
                                "name": _sarif_rule_name(rule.name),
                                "shortDescription": {"text": rule.description},
                                "fullDescription": {"text": rule.description},
                                "defaultConfiguration": {
                                    "level": _sarif_level(rule.severity),
                                },
                                "helpUri": (
                                    "https://github.com/BambooGap/skills-orchestrator"
                                    f"/blob/main/docs/rules/{rule.rule_id}.md"
                                ),
                            }
                            for rule in rules
                        ],
                    }
                },
                "results": [
                    _sarif_result(diagnostic, rule_indexes) for diagnostic in report.diagnostics
                ],
                "invocations": [
                    {
                        "executionSuccessful": not any(
                            d.severity == DiagnosticSeverity.ERROR for d in report.diagnostics
                        )
                    }
                ],
            }
        ],
    }
    return json.dumps(payload, indent=2, ensure_ascii=False) + "\n"


def format_diagnostics_text(report: DiagnosticReport) -> str:
    summary = report.summary()
    lines = [
        "Skills check",
        f"  Skills: {summary['skills']}",
        f"  Zones:  {summary['zones']}",
        f"  Combos: {summary['combos']}",
        (
            "  Findings: "
            f"{summary['errors']} errors, "
            f"{summary['warnings']} warnings, "
            f"{summary['infos']} infos"
        ),
    ]
    if not report.diagnostics:
        lines.append("  OK: no findings")
        return "\n".join(lines) + "\n"

    for diagnostic in report.diagnostics:
        location = ""
        if diagnostic.file:
            location = diagnostic.file
            if diagnostic.line:
                location += f":{diagnostic.line}"
            location = f" ({location})"
        lines.append(
            f"  [{diagnostic.severity.value.upper()}] {diagnostic.rule_id}: "
            f"{diagnostic.message}{location}"
        )
        if diagnostic.suggested_fix:
            lines.append(f"    fix: {diagnostic.suggested_fix}")
    return "\n".join(lines) + "\n"


def _sarif_result(diagnostic: Diagnostic, rule_indexes: dict[str, int]) -> dict[str, Any]:
    result: dict[str, Any] = {
        "ruleId": diagnostic.rule_id,
        "ruleIndex": rule_indexes[diagnostic.rule_id],
        "level": _sarif_level(diagnostic.severity),
        "message": {"text": diagnostic.message},
        "properties": {
            "category": diagnostic.category.value if diagnostic.category else "",
            "skill_id": diagnostic.skill_id or "",
            "suggested_fix": diagnostic.suggested_fix or "",
            **diagnostic.metadata,
        },
    }
    if diagnostic.file:
        physical_location: dict[str, Any] = {
            "artifactLocation": {"uri": diagnostic.file},
        }
        if diagnostic.line:
            physical_location["region"] = {"startLine": diagnostic.line}
        result["locations"] = [{"physicalLocation": physical_location}]
    return result


def _sarif_level(severity: DiagnosticSeverity) -> str:
    return {
        DiagnosticSeverity.ERROR: "error",
        DiagnosticSeverity.WARNING: "warning",
        DiagnosticSeverity.INFO: "note",
    }[severity]


def _sarif_rule_name(name: str) -> str:
    return "".join(part.capitalize() for part in name.split("-"))


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
