"""JSON Schema contracts for Skills Orchestrator artifacts."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator

from . import __version__

MAX_SCHEMA_INPUT_BYTES = 5_000_000
MAX_VALIDATION_ERRORS = 50


@dataclass(frozen=True)
class SchemaDescriptor:
    """Registered schema metadata."""

    kind: str
    filename: str
    title: str
    description: str
    contract_id: str
    stability: str
    since: str
    consumers: tuple[str, ...]

    def to_catalog_entry(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "title": self.title,
            "description": self.description,
            "file": self.filename,
            "contract_id": self.contract_id,
            "stability": self.stability,
            "since": self.since,
            "consumers": list(self.consumers),
        }


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
    "agent-handoff": SchemaDescriptor(
        kind="agent-handoff",
        filename="agent-handoff.schema.json",
        title="Agent Handoff Contract",
        description=(
            "Preview contract for supervisor-to-worker delegation, tenant scope, tool boundaries, "
            "evaluation gates, and evidence requirements."
        ),
        contract_id="skills-orchestrator.agent-handoff.v1",
        stability="preview",
        since="v4.8.8",
        consumers=("agent-runtime", "ci", "platform-review"),
    ),
    "adapter-inspect": SchemaDescriptor(
        kind="adapter-inspect",
        filename="adapter-inspect.schema.json",
        title="Adapter Inspection",
        description="Detected AGENTS.md, Claude Skills, MCP, and Agents SDK surfaces.",
        contract_id="skills-orchestrator.adapters.v1",
        stability="stable",
        since="v3.0.0",
        consumers=("ci", "platform-review", "agent-adapters"),
    ),
    "claude-skills-export": SchemaDescriptor(
        kind="claude-skills-export",
        filename="claude-skills-export.schema.json",
        title="Claude Skills Export Manifest",
        description="Manifest emitted by adapters export claude-skills for round-trip fixtures.",
        contract_id="skills-orchestrator.claude-skills-export.v1",
        stability="stable",
        since="v4.8.9",
        consumers=("ci", "platform-review", "agent-adapters"),
    ),
    "config": SchemaDescriptor(
        kind="config",
        filename="skills-config.schema.json",
        title="Skills Config",
        description="skills.yaml configuration consumed by build, check, and registry.",
        contract_id="skills-orchestrator.config.v1",
        stability="stable",
        since="v2.0.0",
        consumers=("cli", "ci", "platform-review"),
    ),
    "conformance": SchemaDescriptor(
        kind="conformance",
        filename="conformance-report.schema.json",
        title="SkillOps Conformance Report",
        description="Report emitted by conformance run for SkillOps Contract checks.",
        contract_id="skills-orchestrator.conformance.v1",
        stability="stable",
        since="v3.2.0",
        consumers=("ci", "platform-review", "release-gate"),
    ),
    "container-provenance": SchemaDescriptor(
        kind="container-provenance",
        filename="container-provenance.schema.json",
        title="Container Release Provenance",
        description="GHCR image digest, SBOM hash, and attestation subject contract.",
        contract_id="skills-orchestrator.container-provenance.v1",
        stability="stable",
        since="v4.2.0",
        consumers=("supply-chain", "ghcr", "release-gate"),
    ),
    "container-release-verification": SchemaDescriptor(
        kind="container-release-verification",
        filename="container-release-verification.schema.json",
        title="Container Release Verification",
        description="Local release verification report for container provenance and SBOM binding.",
        contract_id="skills-orchestrator.container-release-verification.v1",
        stability="stable",
        since="v4.4.0",
        consumers=("supply-chain", "ci", "release-gate"),
    ),
    "check": SchemaDescriptor(
        kind="check",
        filename="check-report.schema.json",
        title="Check Report",
        description="JSON output from check or validate diagnostics.",
        contract_id="skills-orchestrator.check-report.v1",
        stability="stable",
        since="v2.4.0",
        consumers=("ci", "sarif", "platform-review"),
    ),
    "ci-explainability": SchemaDescriptor(
        kind="ci-explainability",
        filename="ci-explainability.schema.json",
        title="CI Explainability",
        description="CI decision and failure-explainability contract derived from check output.",
        contract_id="skills-orchestrator.ci-explainability.v1",
        stability="stable",
        since="v4.1.0",
        consumers=("ci", "pull-request", "platform-review"),
    ),
    "doctor": SchemaDescriptor(
        kind="doctor",
        filename="doctor-report.schema.json",
        title="Doctor Report",
        description="Commercial readiness report from doctor --format json.",
        contract_id="skills-orchestrator.doctor.v1",
        stability="stable",
        since="v3.0.0",
        consumers=("adoption", "enterprise-readiness", "release-gate"),
    ),
    "evidence": SchemaDescriptor(
        kind="evidence",
        filename="evidence-bundle.schema.json",
        title="Evidence Bundle",
        description="Manifest written by evidence export.",
        contract_id="skills-orchestrator.evidence-bundle.v1",
        stability="stable",
        since="v2.4.0",
        consumers=("ci", "audit", "release-gate"),
    ),
    "enterprise-dashboard-snapshot": SchemaDescriptor(
        kind="enterprise-dashboard-snapshot",
        filename="enterprise-dashboard-snapshot.schema.json",
        title="Enterprise Dashboard Snapshot",
        description="Read-only dashboard contract derived from SkillOps evidence.",
        contract_id="skills-orchestrator.enterprise-dashboard-snapshot.v1",
        stability="preview",
        since="v3.6.0",
        consumers=("dashboard", "hosted-service", "platform-review"),
    ),
    "enterprise-dashboard-rollup": SchemaDescriptor(
        kind="enterprise-dashboard-rollup",
        filename="enterprise-dashboard-rollup.schema.json",
        title="Enterprise Dashboard Rollup",
        description="Organization-level rollup derived from dashboard snapshots.",
        contract_id="skills-orchestrator.enterprise-dashboard-rollup.v1",
        stability="preview",
        since="v3.8.0",
        consumers=("dashboard", "hosted-service", "platform-review"),
    ),
    "github-app-installation": SchemaDescriptor(
        kind="github-app-installation",
        filename="github-app-installation.schema.json",
        title="GitHub App Installation",
        description="Minimal installation contract for future GitHub App ingestion.",
        contract_id="skills-orchestrator.github-app-installation.v1",
        stability="preview",
        since="v3.0.0",
        consumers=("github-app", "hosted-service"),
    ),
    "hosted-registry-ingest": SchemaDescriptor(
        kind="hosted-registry-ingest",
        filename="hosted-registry-ingest.schema.json",
        title="Hosted Registry Ingest",
        description="Hosted registry handoff contract for OSS-generated artifacts.",
        contract_id="skills-orchestrator.hosted-registry-ingest.v1",
        stability="preview",
        since="v3.0.0",
        consumers=("hosted-registry", "platform-review"),
    ),
    "manifest": SchemaDescriptor(
        kind="manifest",
        filename="instruction-manifest.schema.json",
        title="Instruction Manifest",
        description="Native instruction manifest output.",
        contract_id="skills-orchestrator.instruction-manifest.v1",
        stability="stable",
        since="v2.3.0",
        consumers=("cli", "ci", "agent-adapters"),
    ),
    "multi-repo-artifacts": SchemaDescriptor(
        kind="multi-repo-artifacts",
        filename="multi-repo-artifacts.schema.json",
        title="Multi-repository Artifacts",
        description="Organization-level index over multiple repository evidence bundles.",
        contract_id="skills-orchestrator.multi-repo-artifacts.v1",
        stability="stable",
        since="v4.5.0",
        consumers=("ci", "audit", "platform-review", "hosted-registry"),
    ),
    "policy-opa-input": SchemaDescriptor(
        kind="policy-opa-input",
        filename="policy-opa-input.schema.json",
        title="Policy OPA Input",
        description="OPA input document exported for policy-as-code proofs.",
        contract_id="skills-orchestrator.policy-opa-input.v1",
        stability="stable",
        since="v2.4.0",
        consumers=("policy-as-code", "ci", "audit"),
    ),
    "policy-pack": SchemaDescriptor(
        kind="policy-pack",
        filename="policy-pack.schema.json",
        title="Declarative Policy Pack",
        description="Safe YAML/JSON policy pack for local SkillOps governance rules.",
        contract_id="skills-orchestrator.policy-pack.v1",
        stability="stable",
        since="v3.2.0",
        consumers=("ci", "platform-policy", "release-gate"),
    ),
    "post-release-smoke": SchemaDescriptor(
        kind="post-release-smoke",
        filename="post-release-smoke.schema.json",
        title="Post-release Smoke Report",
        description=(
            "Public artifact smoke report for GitHub Release, PyPI, GHCR, and adopter path checks."
        ),
        contract_id="skills-orchestrator.post-release-smoke.v1",
        stability="stable",
        since="v4.7.11",
        consumers=("ci", "release-gate", "platform-review"),
    ),
    "registry": SchemaDescriptor(
        kind="registry",
        filename="skill-registry.schema.json",
        title="Skill Registry",
        description="Organization-level registry export.",
        contract_id="skills-orchestrator.registry.v1",
        stability="stable",
        since="v2.5.0",
        consumers=("registry", "ci", "platform-review"),
    ),
    "registry-diff": SchemaDescriptor(
        kind="registry-diff",
        filename="registry-diff.schema.json",
        title="Registry Diff",
        description="Diff between two registry JSON exports.",
        contract_id="skills-orchestrator.registry-diff.v1",
        stability="stable",
        since="v2.7.0",
        consumers=("pull-request", "ci", "platform-review"),
    ),
    "registry-graph": SchemaDescriptor(
        kind="registry-graph",
        filename="registry-graph.schema.json",
        title="Registry Graph",
        description="Graph export for skill ownership, source, combo, and conflict relationships.",
        contract_id="skills-orchestrator.registry-graph.v1",
        stability="stable",
        since="v3.4.0",
        consumers=("registry", "graph-viewer", "platform-review"),
    ),
    "schema-catalog": SchemaDescriptor(
        kind="schema-catalog",
        filename="schema-catalog.schema.json",
        title="Schema Catalog",
        description="Machine-readable catalog emitted by schema list --format json.",
        contract_id="skills-orchestrator.schema-catalog.v1",
        stability="stable",
        since="v3.9.0",
        consumers=("ci", "platform-review", "contract-audit"),
    ),
    "schema-audit": SchemaDescriptor(
        kind="schema-audit",
        filename="schema-audit.schema.json",
        title="Schema Audit Report",
        description="Self-audit report for packaged schema contracts and catalog metadata.",
        contract_id="skills-orchestrator.schema-audit.v1",
        stability="stable",
        since="v4.0.0",
        consumers=("ci", "platform-review", "contract-audit"),
    ),
    "supply-chain-sbom": SchemaDescriptor(
        kind="supply-chain-sbom",
        filename="supply-chain-sbom.schema.json",
        title="Supply-chain SBOM",
        description="CycloneDX SBOM generated by supply-chain sbom.",
        contract_id="CycloneDX-1.5",
        stability="stable",
        since="v2.9.0",
        consumers=("supply-chain", "ci", "audit"),
    ),
}


def list_schema_descriptors() -> list[SchemaDescriptor]:
    """Return registered schemas in stable display order."""
    return [SCHEMAS[key] for key in sorted(SCHEMAS)]


def build_schema_catalog() -> dict[str, Any]:
    """Return the machine-readable catalog for registered schemas."""
    return {
        "schema_version": "skills-orchestrator.schema-catalog.v1",
        "schemas": [descriptor.to_catalog_entry() for descriptor in list_schema_descriptors()],
    }


def audit_schema_catalog() -> dict[str, Any]:
    """Audit packaged schemas and catalog metadata without reading project files."""
    checks: list[dict[str, Any]] = []
    descriptors = list_schema_descriptors()
    for descriptor in descriptors:
        _add_schema_load_check(checks, descriptor)
        _add_descriptor_metadata_check(checks, descriptor)

    catalog = build_schema_catalog()
    try:
        Draft202012Validator(load_schema("schema-catalog")).validate(catalog)
        checks.append(
            {
                "id": "schema-catalog:self-validation",
                "kind": "schema-catalog",
                "status": "pass",
                "message": "schema catalog validates against schema-catalog.schema.json",
            }
        )
    except Exception as exc:
        checks.append(
            {
                "id": "schema-catalog:self-validation",
                "kind": "schema-catalog",
                "status": "fail",
                "message": str(exc),
            }
        )

    failed = sum(1 for check in checks if check["status"] == "fail")
    return {
        "schema_version": "skills-orchestrator.schema-audit.v1",
        "tool": {"name": "skills-orchestrator", "version": __version__},
        "status": "pass" if failed == 0 else "fail",
        "summary": {
            "schemas": len(descriptors),
            "stable": sum(1 for item in descriptors if item.stability == "stable"),
            "preview": sum(1 for item in descriptors if item.stability == "preview"),
            "checks": len(checks),
            "passed": len(checks) - failed,
            "failed": failed,
        },
        "checks": checks,
    }


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


def _add_schema_load_check(checks: list[dict[str, Any]], descriptor: SchemaDescriptor) -> None:
    try:
        load_schema(descriptor.kind)
        checks.append(
            {
                "id": f"schema-load:{descriptor.kind}",
                "kind": descriptor.kind,
                "status": "pass",
                "message": f"{descriptor.filename} is packaged and valid Draft 2020-12 JSON Schema",
            }
        )
    except Exception as exc:
        checks.append(
            {
                "id": f"schema-load:{descriptor.kind}",
                "kind": descriptor.kind,
                "status": "fail",
                "message": str(exc),
            }
        )


def _add_descriptor_metadata_check(
    checks: list[dict[str, Any]], descriptor: SchemaDescriptor
) -> None:
    errors: list[str] = []
    if descriptor.stability not in {"stable", "preview"}:
        errors.append("stability must be stable or preview")
    if not re.fullmatch(r"v\d+\.\d+\.\d+", descriptor.since):
        errors.append("since must use vMAJOR.MINOR.PATCH")
    if descriptor.contract_id.startswith(
        "skills-orchestrator."
    ) and not descriptor.contract_id.endswith(".v1"):
        errors.append("skills-orchestrator contract ids must end in .v1")
    if not descriptor.consumers:
        errors.append("consumers must not be empty")

    checks.append(
        {
            "id": f"schema-metadata:{descriptor.kind}",
            "kind": descriptor.kind,
            "status": "fail" if errors else "pass",
            "message": "; ".join(errors) if errors else "catalog metadata is valid",
        }
    )


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
