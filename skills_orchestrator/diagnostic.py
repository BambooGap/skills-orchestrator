"""Diagnostic model for machine-readable skill checks."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class DiagnosticSeverity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class DiagnosticCategory(str, Enum):
    CONFLICT = "conflict"
    STRUCTURE = "structure"
    METADATA = "metadata"
    LOCK = "lock"
    INHERITANCE = "inheritance"


@dataclass(frozen=True)
class DiagnosticRule:
    rule_id: str
    name: str
    severity: DiagnosticSeverity
    category: DiagnosticCategory
    description: str


RULES: dict[str, DiagnosticRule] = {
    "SO000": DiagnosticRule(
        rule_id="SO000",
        name="fatal-error",
        severity=DiagnosticSeverity.ERROR,
        category=DiagnosticCategory.STRUCTURE,
        description="The check could not complete because configuration or input parsing failed.",
    ),
    "SO001": DiagnosticRule(
        rule_id="SO001",
        name="missing-description",
        severity=DiagnosticSeverity.WARNING,
        category=DiagnosticCategory.METADATA,
        description="Skill metadata should include a summary or official description.",
    ),
    "SO002": DiagnosticRule(
        rule_id="SO002",
        name="duplicate-skill-id",
        severity=DiagnosticSeverity.WARNING,
        category=DiagnosticCategory.STRUCTURE,
        description="Multiple skill files resolve to the same skill id.",
    ),
    "SO003": DiagnosticRule(
        rule_id="SO003",
        name="unresolved-conflict",
        severity=DiagnosticSeverity.ERROR,
        category=DiagnosticCategory.CONFLICT,
        description="A declared conflict cannot be resolved by policy and priority.",
    ),
    "SO004": DiagnosticRule(
        rule_id="SO004",
        name="asymmetric-conflict-declaration",
        severity=DiagnosticSeverity.WARNING,
        category=DiagnosticCategory.CONFLICT,
        description="A one-way conflict declaration is valid but weaker for auditability.",
    ),
    "SO005": DiagnosticRule(
        rule_id="SO005",
        name="oversized-skill",
        severity=DiagnosticSeverity.INFO,
        category=DiagnosticCategory.METADATA,
        description="Skill content is large enough to deserve review before runtime injection.",
    ),
    "SO007": DiagnosticRule(
        rule_id="SO007",
        name="lock-drift",
        severity=DiagnosticSeverity.WARNING,
        category=DiagnosticCategory.LOCK,
        description="Current resolved skills differ from the lock file.",
    ),
    "SO008": DiagnosticRule(
        rule_id="SO008",
        name="missing-owner",
        severity=DiagnosticSeverity.WARNING,
        category=DiagnosticCategory.METADATA,
        description="Team policy requires skill owner metadata.",
    ),
    "SO009": DiagnosticRule(
        rule_id="SO009",
        name="missing-source",
        severity=DiagnosticSeverity.WARNING,
        category=DiagnosticCategory.METADATA,
        description="Team policy requires skill source metadata.",
    ),
    "SO010": DiagnosticRule(
        rule_id="SO010",
        name="missing-version",
        severity=DiagnosticSeverity.WARNING,
        category=DiagnosticCategory.METADATA,
        description="Team policy requires skill version metadata.",
    ),
    "SO011": DiagnosticRule(
        rule_id="SO011",
        name="invalid-lifecycle",
        severity=DiagnosticSeverity.ERROR,
        category=DiagnosticCategory.METADATA,
        description="Team policy only allows supported skill lifecycle states.",
    ),
    "SO012": DiagnosticRule(
        rule_id="SO012",
        name="required-skill-without-approver",
        severity=DiagnosticSeverity.WARNING,
        category=DiagnosticCategory.METADATA,
        description="Required runtime skills should carry approver metadata.",
    ),
}


@dataclass
class Diagnostic:
    rule_id: str
    severity: DiagnosticSeverity
    message: str
    file: str | None = None
    line: int | None = None
    skill_id: str | None = None
    category: DiagnosticCategory | None = None
    suggested_fix: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_rule(
        cls,
        rule_id: str,
        message: str,
        *,
        file: str | None = None,
        line: int | None = None,
        skill_id: str | None = None,
        suggested_fix: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> "Diagnostic":
        rule = RULES[rule_id]
        return cls(
            rule_id=rule.rule_id,
            severity=rule.severity,
            message=message,
            file=file,
            line=line,
            skill_id=skill_id,
            category=rule.category,
            suggested_fix=suggested_fix,
            metadata=metadata or {},
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "severity": self.severity.value,
            "message": self.message,
            "file": self.file,
            "line": self.line,
            "skill_id": self.skill_id,
            "category": self.category.value if self.category else None,
            "suggested_fix": self.suggested_fix,
            "metadata": self.metadata,
        }


@dataclass
class DiagnosticReport:
    diagnostics: list[Diagnostic]
    total_skills: int
    zones: int
    combos: int

    def summary(self) -> dict[str, int]:
        errors = sum(1 for d in self.diagnostics if d.severity == DiagnosticSeverity.ERROR)
        warnings = sum(1 for d in self.diagnostics if d.severity == DiagnosticSeverity.WARNING)
        infos = sum(1 for d in self.diagnostics if d.severity == DiagnosticSeverity.INFO)
        return {
            "total": len(self.diagnostics),
            "errors": errors,
            "warnings": warnings,
            "infos": infos,
            "skills": self.total_skills,
            "zones": self.zones,
            "combos": self.combos,
        }
