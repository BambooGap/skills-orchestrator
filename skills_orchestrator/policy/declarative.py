"""Declarative policy pack loader and evaluator.

Declarative packs are intentionally data-only. They never import Python code from
the target repository, which keeps PR/CI policy evaluation safe by default.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from skills_orchestrator.diagnostic import (
    Diagnostic,
    DiagnosticCategory,
    DiagnosticSeverity,
)
from skills_orchestrator.models import Config, SkillMeta
from skills_orchestrator.schema_validation import validate_document

SKILL_POLICY_FIELDS = {
    "id",
    "name",
    "summary",
    "tags",
    "load_policy",
    "priority",
    "zones",
    "conflict_with",
    "base",
    "owner",
    "source",
    "version",
    "lifecycle",
    "approvers",
    "reviewed_at",
    "expires_at",
    "license",
    "provenance",
}
ALLOWED_VALUE_POLICY_FIELDS = {
    "id",
    "name",
    "summary",
    "load_policy",
    "base",
    "owner",
    "source",
    "version",
    "lifecycle",
    "reviewed_at",
    "expires_at",
    "license",
}


@dataclass(frozen=True)
class DeclarativePolicyPack:
    """A validated local policy pack loaded from YAML or JSON."""

    pack_id: str
    path: Path
    name: str
    description: str
    rules: list[dict[str, Any]]


def load_declarative_policy_pack(path_text: str) -> DeclarativePolicyPack:
    """Load and schema-validate a local declarative policy pack."""
    path = Path(path_text).expanduser()
    if not path.exists():
        raise FileNotFoundError(f"Policy pack file does not exist: {path}")
    result = validate_document("policy-pack", str(path))
    if not result.valid:
        details = "; ".join(f"{error.path}: {error.message}" for error in result.errors)
        raise ValueError(f"Invalid policy pack {path}: {details}")
    data = _load_policy_pack_document(str(path))
    return DeclarativePolicyPack(
        pack_id=str(data["id"]),
        path=path.resolve(),
        name=str(data.get("name") or data["id"]),
        description=str(data.get("description") or ""),
        rules=list(data.get("rules") or []),
    )


def _load_policy_pack_document(path_text: str) -> dict[str, Any]:
    """Load a policy pack document after schema validation."""
    from skills_orchestrator.schema_validation import load_document

    document = load_document(path_text, kind="policy-pack")
    if not isinstance(document, dict):
        raise ValueError("Policy pack must be a mapping")
    return document


def declarative_policy_pack_diagnostics(
    cfg: Config, pack: DeclarativePolicyPack
) -> list[Diagnostic]:
    """Evaluate a declarative pack against parsed skills metadata."""
    diagnostics: list[Diagnostic] = []
    for rule in pack.rules:
        rule_id = str(rule["id"])
        severity = _severity(rule.get("severity", "warning"))
        required_fields = rule.get("required_fields") or []
        allowed_values = rule.get("allowed_values") or []
        for skill in cfg.skills:
            path = _skill_path(cfg, skill)
            rel = _relative_path(path, Path(cfg.base_dir))
            for field in required_fields:
                value = _field_value(skill, str(field))
                if _is_missing(value):
                    diagnostics.append(
                        _custom_policy_diagnostic(
                            severity,
                            f"Skill '{skill.id}' is missing field '{field}' required by policy pack {pack.pack_id}.",
                            file=rel,
                            skill_id=skill.id,
                            suggested_fix=f"Add {field}: <value> to the skill metadata.",
                            metadata={
                                "policy_pack": pack.pack_id,
                                "policy_pack_path": str(pack.path),
                                "declarative_rule": rule_id,
                                "field": field,
                            },
                        )
                    )
            for item in allowed_values:
                field = str(item["field"])
                allowed = [str(value) for value in item["values"]]
                value = _allowed_field_value(skill, field)
                if _is_missing(value):
                    continue
                if str(value) not in allowed:
                    diagnostics.append(
                        _custom_policy_diagnostic(
                            severity,
                            f"Skill '{skill.id}' field '{field}' value '{value}' is not allowed by policy pack {pack.pack_id}.",
                            file=rel,
                            skill_id=skill.id,
                            suggested_fix=f"Use one of: {', '.join(allowed)}.",
                            metadata={
                                "policy_pack": pack.pack_id,
                                "policy_pack_path": str(pack.path),
                                "declarative_rule": rule_id,
                                "field": field,
                                "allowed_values": allowed,
                            },
                        )
                    )
    return diagnostics


def _custom_policy_diagnostic(
    severity: DiagnosticSeverity,
    message: str,
    *,
    file: str,
    skill_id: str,
    suggested_fix: str,
    metadata: dict[str, Any],
) -> Diagnostic:
    return Diagnostic(
        rule_id="SO017",
        severity=severity,
        message=message,
        file=file,
        line=1,
        skill_id=skill_id,
        category=DiagnosticCategory.METADATA,
        suggested_fix=suggested_fix,
        metadata=metadata,
    )


def _severity(value: Any) -> DiagnosticSeverity:
    try:
        return DiagnosticSeverity(str(value))
    except ValueError as exc:
        raise ValueError(f"Unsupported declarative policy severity: {value}") from exc


def _field_value(skill: SkillMeta, field: str) -> Any:
    if field not in SKILL_POLICY_FIELDS:
        raise ValueError(f"Unsupported declarative policy field: {field}")
    return getattr(skill, field)


def _allowed_field_value(skill: SkillMeta, field: str) -> Any:
    if field not in ALLOWED_VALUE_POLICY_FIELDS:
        allowed = ", ".join(sorted(ALLOWED_VALUE_POLICY_FIELDS))
        raise ValueError(f"allowed_values only supports scalar fields: {allowed}")
    return getattr(skill, field)


def _is_missing(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, list):
        return not value
    if isinstance(value, dict):
        return not value
    return False


def _skill_path(cfg: Config, skill: SkillMeta) -> Path:
    path = Path(skill.path)
    if path.is_absolute():
        return path
    return (Path(cfg.base_dir) / path).resolve()


def _relative_path(path: Path, base: Path) -> str:
    try:
        return str(path.resolve().relative_to(base.resolve()))
    except ValueError:
        return str(path)
