"""JSON Schema contracts for Skills Orchestrator artifacts."""

from __future__ import annotations

import json
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator

MAX_SCHEMA_INPUT_BYTES = 5_000_000
MAX_VALIDATION_ERRORS = 50


@dataclass(frozen=True)
class SchemaDescriptor:
    """Registered schema metadata."""

    kind: str
    filename: str
    title: str
    description: str


@dataclass(frozen=True)
class ValidationIssue:
    """A single JSON Schema validation issue."""

    path: str
    message: str
    schema_path: str

    def to_dict(self) -> dict[str, str]:
        return {
            "path": self.path,
            "message": self.message,
            "schema_path": self.schema_path,
        }


@dataclass(frozen=True)
class ValidationResult:
    """Result returned by schema validation."""

    kind: str
    input_path: str
    schema: SchemaDescriptor
    valid: bool
    errors: list[ValidationIssue]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "skills-orchestrator.schema-validation.v1",
            "kind": self.kind,
            "input": self.input_path,
            "schema": {
                "title": self.schema.title,
                "file": self.schema.filename,
            },
            "valid": self.valid,
            "errors": [error.to_dict() for error in self.errors],
        }


SCHEMAS: dict[str, SchemaDescriptor] = {
    "adapter-inspect": SchemaDescriptor(
        kind="adapter-inspect",
        filename="adapter-inspect.schema.json",
        title="Adapter Inspection",
        description="Detected AGENTS.md, Claude Skills, MCP, and Agents SDK surfaces.",
    ),
    "config": SchemaDescriptor(
        kind="config",
        filename="skills-config.schema.json",
        title="Skills Config",
        description="skills.yaml configuration consumed by build, check, and registry.",
    ),
    "conformance": SchemaDescriptor(
        kind="conformance",
        filename="conformance-report.schema.json",
        title="SkillOps Conformance Report",
        description="Report emitted by conformance run for SkillOps Contract checks.",
    ),
    "check": SchemaDescriptor(
        kind="check",
        filename="check-report.schema.json",
        title="Check Report",
        description="JSON output from check or validate diagnostics.",
    ),
    "doctor": SchemaDescriptor(
        kind="doctor",
        filename="doctor-report.schema.json",
        title="Doctor Report",
        description="Commercial readiness report from doctor --format json.",
    ),
    "evidence": SchemaDescriptor(
        kind="evidence",
        filename="evidence-bundle.schema.json",
        title="Evidence Bundle",
        description="Manifest written by evidence export.",
    ),
    "enterprise-dashboard-snapshot": SchemaDescriptor(
        kind="enterprise-dashboard-snapshot",
        filename="enterprise-dashboard-snapshot.schema.json",
        title="Enterprise Dashboard Snapshot",
        description="Read-only dashboard contract derived from SkillOps evidence.",
    ),
    "github-app-installation": SchemaDescriptor(
        kind="github-app-installation",
        filename="github-app-installation.schema.json",
        title="GitHub App Installation",
        description="Minimal installation contract for future GitHub App ingestion.",
    ),
    "hosted-registry-ingest": SchemaDescriptor(
        kind="hosted-registry-ingest",
        filename="hosted-registry-ingest.schema.json",
        title="Hosted Registry Ingest",
        description="Hosted registry handoff contract for OSS-generated artifacts.",
    ),
    "manifest": SchemaDescriptor(
        kind="manifest",
        filename="instruction-manifest.schema.json",
        title="Instruction Manifest",
        description="Native instruction manifest output.",
    ),
    "policy-opa-input": SchemaDescriptor(
        kind="policy-opa-input",
        filename="policy-opa-input.schema.json",
        title="Policy OPA Input",
        description="OPA input document exported for policy-as-code proofs.",
    ),
    "policy-pack": SchemaDescriptor(
        kind="policy-pack",
        filename="policy-pack.schema.json",
        title="Declarative Policy Pack",
        description="Safe YAML/JSON policy pack for local SkillOps governance rules.",
    ),
    "registry": SchemaDescriptor(
        kind="registry",
        filename="skill-registry.schema.json",
        title="Skill Registry",
        description="Organization-level registry export.",
    ),
    "registry-diff": SchemaDescriptor(
        kind="registry-diff",
        filename="registry-diff.schema.json",
        title="Registry Diff",
        description="Diff between two registry JSON exports.",
    ),
    "supply-chain-sbom": SchemaDescriptor(
        kind="supply-chain-sbom",
        filename="supply-chain-sbom.schema.json",
        title="Supply-chain SBOM",
        description="CycloneDX SBOM generated by supply-chain sbom.",
    ),
}


def list_schema_descriptors() -> list[SchemaDescriptor]:
    """Return registered schemas in stable display order."""
    return [SCHEMAS[key] for key in sorted(SCHEMAS)]


def load_schema(kind: str) -> dict[str, Any]:
    """Load a registered JSON Schema."""
    descriptor = _descriptor(kind)
    schema_text = (
        files("skills_orchestrator")
        .joinpath("schemas")
        .joinpath(descriptor.filename)
        .read_text(encoding="utf-8")
    )
    schema = json.loads(schema_text)
    Draft202012Validator.check_schema(schema)
    return schema


def load_document(input_path: str, *, kind: str) -> Any:
    """Load JSON or YAML input for schema validation."""
    path = Path(input_path)
    if path.stat().st_size > MAX_SCHEMA_INPUT_BYTES:
        raise ValueError(
            f"Input file is too large for schema validation "
            f"({path.stat().st_size} bytes > {MAX_SCHEMA_INPUT_BYTES} bytes)."
        )
    text = path.read_text(encoding="utf-8")
    if kind == "config" or path.suffix.lower() in {".yaml", ".yml"}:
        return yaml.safe_load(text) or {}
    return json.loads(text)


def validate_document(kind: str, input_path: str) -> ValidationResult:
    """Validate a file against one of the registered schemas."""
    descriptor = _descriptor(kind)
    document = load_document(input_path, kind=kind)
    validator = Draft202012Validator(load_schema(kind))
    validation_errors = sorted(validator.iter_errors(document), key=lambda item: item.json_path)
    issues = [
        ValidationIssue(
            path=_format_error_path(error.absolute_path),
            message=error.message,
            schema_path=_format_error_path(error.absolute_schema_path),
        )
        for error in validation_errors[:MAX_VALIDATION_ERRORS]
    ]
    return ValidationResult(
        kind=kind,
        input_path=input_path,
        schema=descriptor,
        valid=not issues,
        errors=issues,
    )


def _descriptor(kind: str) -> SchemaDescriptor:
    try:
        return SCHEMAS[kind]
    except KeyError as exc:
        known = ", ".join(sorted(SCHEMAS))
        raise ValueError(f"Unknown schema kind '{kind}'. Known kinds: {known}") from exc


def _format_error_path(parts: Any) -> str:
    items = list(parts)
    if not items:
        return "$"
    path = "$"
    for item in items:
        if isinstance(item, int):
            path += f"[{item}]"
        else:
            path += f".{item}"
    return path
