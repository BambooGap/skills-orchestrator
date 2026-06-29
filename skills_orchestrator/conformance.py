"""SkillOps conformance runner."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from skills_orchestrator import __version__
from skills_orchestrator.adapters import inspect_adapters
from skills_orchestrator.checker import run_check
from skills_orchestrator.evidence import export_evidence_bundle
from skills_orchestrator.schema_validation import validate_document


@dataclass
class ConformanceStep:
    """A single conformance assertion."""

    id: str
    title: str
    status: str
    detail: str = ""
    artifact: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "status": self.status,
            "detail": self.detail,
            "artifact": self.artifact,
            "metadata": self.metadata,
        }


def run_conformance(
    config_path: str,
    *,
    project_root: str = ".",
    zone_id: str | None = None,
    policy_packs: tuple[str, ...] | list[str] = (),
    profile: str = "core",
    fail_on: str = "error",
) -> dict[str, Any]:
    """Run the local SkillOps Contract conformance suite."""
    if profile not in {"core", "enterprise"}:
        raise ValueError("conformance profile must be 'core' or 'enterprise'")

    steps: list[ConformanceStep] = []
    steps.append(_schema_step("config-schema", "Config schema", "config", config_path))

    check_report = run_check(config_path, zone_id=zone_id, policy_packs=policy_packs)
    check_summary = check_report.summary()
    if check_summary["errors"]:
        check_status = "fail"
    elif check_summary["warnings"]:
        check_status = "warn"
    else:
        check_status = "pass"
    steps.append(
        ConformanceStep(
            id="check-contract",
            title="Check diagnostics contract",
            status=check_status,
            detail=(
                f"{check_summary['errors']} errors, "
                f"{check_summary['warnings']} warnings, {check_summary['infos']} infos"
            ),
            metadata={"summary": check_summary},
        )
    )
    steps.append(
        ConformanceStep(
            id="policy-trace",
            title="Policy trace contract",
            status="pass" if check_report.policy_trace else "fail",
            detail=(
                f"{len(check_report.policy_trace)} trace entries"
                if check_report.policy_trace
                else "missing policy_trace entries"
            ),
            metadata={"trace_entries": len(check_report.policy_trace)},
        )
    )

    with TemporaryDirectory(prefix="skills-orchestrator-conformance-") as temp_dir:
        bundle = export_evidence_bundle(
            config_path,
            temp_dir,
            zone_id=zone_id,
            policy_packs=policy_packs,
        )
        manifest_path = Path(temp_dir) / "evidence-manifest.json"
        steps.append(
            _schema_step(
                "evidence-manifest",
                "Evidence bundle manifest",
                "evidence",
                manifest_path,
                artifact_label="evidence/evidence-manifest.json",
            )
        )
        steps.append(_evidence_ledger_step(bundle))
        ci_explainability_artifact = bundle["files"].get("ci_explainability")
        steps.append(
            _schema_step(
                "ci-explainability",
                "CI explainability contract",
                "ci-explainability",
                ci_explainability_artifact or "",
                artifact_label="evidence/ci-explainability.json",
            )
        )
        evidence_schemas = {
            "check_json": "check",
            "instruction_manifest": "manifest",
            "opa_input": "policy-opa-input",
            "doctor": "doctor",
            "registry": "registry",
        }
        for label, kind in evidence_schemas.items():
            artifact = bundle["files"].get(label)
            steps.append(
                _schema_step(
                    f"evidence-{label}",
                    f"Evidence artifact: {label}",
                    kind,
                    artifact or "",
                    artifact_label=f"evidence/{Path(artifact).name}" if artifact else "",
                )
            )

        registry_graph_artifact = bundle["files"].get("registry_graph")
        steps.append(
            _schema_step(
                "registry-graph",
                "Registry graph contract",
                "registry-graph",
                registry_graph_artifact or "",
                artifact_label="evidence/registry-graph.json",
            )
        )

        adapter_path = Path(temp_dir) / "adapter-inspect.json"
        adapter_path.write_text(
            json.dumps(inspect_adapters(project_root), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        steps.append(
            _schema_step(
                "adapter-inspect",
                "Adapter inspection contract",
                "adapter-inspect",
                adapter_path,
                artifact_label="adapter-inspect.json",
            )
        )

    steps.append(_negative_conformance_step())

    if profile == "enterprise":
        enterprise_blockers = [
            step
            for step in steps
            if step.status == "fail" or (fail_on == "warning" and step.status in {"fail", "warn"})
        ]
        steps.append(
            ConformanceStep(
                id="enterprise-gate",
                title="Enterprise readiness gate",
                status="fail" if enterprise_blockers else "pass",
                detail=(
                    "All required evidence contracts are valid."
                    if not enterprise_blockers
                    else f"{len(enterprise_blockers)} blocking conformance steps."
                ),
                metadata={"blocking_steps": [step.id for step in enterprise_blockers]},
            )
        )

    summary = _summary(steps)
    return {
        "schema_version": "skills-orchestrator.conformance.v1",
        "generated_at": _now_iso(),
        "tool": {"name": "skills-orchestrator", "version": __version__},
        "profile": profile,
        "config": config_path,
        "zone": zone_id or "default",
        "policy_packs": list(policy_packs),
        "status": _overall_status(summary),
        "summary": summary,
        "steps": [step.to_dict() for step in steps],
    }


def format_conformance_text(payload: dict[str, Any]) -> str:
    """Render a conformance payload for terminal use."""
    lines = [
        f"SkillOps conformance: {payload['status']}",
        (
            "Summary: "
            f"{payload['summary']['passed']} passed, "
            f"{payload['summary']['warnings']} warnings, "
            f"{payload['summary']['failed']} failed"
        ),
        "",
        "Steps:",
    ]
    for step in payload["steps"]:
        marker = {"pass": "OK", "warn": "WARN", "fail": "FAIL"}[step["status"]]
        detail = f" - {step['detail']}" if step.get("detail") else ""
        lines.append(f"  [{marker}] {step['id']}: {step['title']}{detail}")
    return "\n".join(lines) + "\n"


def _schema_step(
    step_id: str,
    title: str,
    kind: str,
    path_value: str | Path,
    *,
    artifact_label: str | None = None,
) -> ConformanceStep:
    path = Path(path_value)
    artifact = artifact_label if artifact_label is not None else str(path)
    if not str(path_value):
        return ConformanceStep(step_id, title, "fail", detail="missing artifact path")
    if not path.exists():
        return ConformanceStep(step_id, title, "fail", detail="missing artifact", artifact=artifact)
    try:
        result = validate_document(kind, str(path))
    except Exception as exc:
        return ConformanceStep(step_id, title, "fail", detail=str(exc), artifact=artifact)
    if result.valid:
        return ConformanceStep(step_id, title, "pass", detail="schema valid", artifact=artifact)
    return ConformanceStep(
        step_id,
        title,
        "fail",
        detail="; ".join(f"{issue.path}: {issue.message}" for issue in result.errors[:3]),
        artifact=artifact,
    )


def _summary(steps: list[ConformanceStep]) -> dict[str, int]:
    return {
        "total": len(steps),
        "passed": sum(1 for step in steps if step.status == "pass"),
        "warnings": sum(1 for step in steps if step.status == "warn"),
        "failed": sum(1 for step in steps if step.status == "fail"),
    }


def _overall_status(summary: dict[str, int]) -> str:
    if summary["failed"]:
        return "fail"
    if summary["warnings"]:
        return "warn"
    return "pass"


def conformance_should_fail(payload: dict[str, Any], fail_on: str) -> bool:
    """Return whether CLI should exit non-zero for a conformance payload."""
    if fail_on == "never":
        return False
    summary = payload["summary"]
    if fail_on == "warning":
        return bool(summary["failed"] or summary["warnings"])
    return bool(summary["failed"])


def _negative_conformance_step() -> ConformanceStep:
    """Verify representative invalid projects trigger the expected checks."""
    cases = [
        {
            "id": "missing-governance-metadata",
            "policy_packs": ["builtin/team-standard"],
            "skills": [
                "---\n"
                "id: missing-governance\n"
                "name: Missing Governance\n"
                "summary: Missing owner/source/version\n"
                "---\n"
                "# Missing Governance\n"
            ],
            "expected_rules": {"SO008", "SO009", "SO010"},
        },
        {
            "id": "invalid-skill-load-policy",
            "policy_packs": [],
            "skills": [
                "---\n"
                "id: invalid-policy\n"
                "name: Invalid Policy\n"
                "summary: Invalid load policy\n"
                "load_policy: sometimes\n"
                "---\n"
                "# Invalid Policy\n"
            ],
            "expected_rules": {"SO013"},
        },
        {
            "id": "invalid-lifecycle-and-required-approvers",
            "policy_packs": ["builtin/team-standard"],
            "skills": [
                "---\n"
                "id: required-without-approvers\n"
                "name: Required Without Approvers\n"
                "summary: Required skill without approvers\n"
                "load_policy: require\n"
                "owner: platform-team\n"
                "source: internal://skills/required-without-approvers\n"
                "version: 1.0.0\n"
                "lifecycle: archived\n"
                "---\n"
                "# Required Without Approvers\n"
            ],
            "expected_rules": {"SO011", "SO012"},
        },
        {
            "id": "invalid-review-window",
            "policy_packs": ["builtin/engineering-grade"],
            "skills": [
                "---\n"
                "id: invalid-review-window\n"
                "name: Invalid Review Window\n"
                "summary: Invalid review-window dates\n"
                "owner: platform-team\n"
                "source: internal://skills/invalid-review-window\n"
                "version: 1.0.0\n"
                "lifecycle: active\n"
                "reviewed_at: yesterday\n"
                "expires_at: 2999-01-01\n"
                "license: MIT\n"
                "---\n"
                "# Invalid Review Window\n"
            ],
            "expected_rules": {"SO015"},
        },
        {
            "id": "expired-review-window",
            "policy_packs": ["builtin/engineering-grade"],
            "skills": [
                "---\n"
                "id: expired-review-window\n"
                "name: Expired Review Window\n"
                "summary: Expired review-window dates\n"
                "owner: platform-team\n"
                "source: internal://skills/expired-review-window\n"
                "version: 1.0.0\n"
                "lifecycle: active\n"
                "reviewed_at: 2000-01-01\n"
                "expires_at: 2000-01-02\n"
                "license: MIT\n"
                "---\n"
                "# Expired Review Window\n"
            ],
            "expected_rules": {"SO016"},
        },
        {
            "id": "external-provenance-and-license",
            "policy_packs": ["builtin/engineering-grade"],
            "skills": [
                "---\n"
                "id: external-skill\n"
                "name: External Skill\n"
                "summary: External skill without provenance\n"
                "owner: platform-team\n"
                "source: https://example.com/skills/external-skill.md\n"
                "version: 1.0.0\n"
                "lifecycle: active\n"
                "license: GPL-3.0\n"
                "---\n"
                "# External Skill\n"
            ],
            "expected_rules": {"SO014", "SO019", "SO020"},
        },
        {
            "id": "duplicate-skill-id",
            "policy_packs": [],
            "skills": [
                "---\nid: duplicate\nname: Duplicate A\nsummary: A\n---\n# A\n",
                "---\nid: duplicate\nname: Duplicate B\nsummary: B\n---\n# B\n",
            ],
            "expected_rules": {"SO002"},
        },
    ]
    results = [_run_negative_case(case) for case in cases]
    passed = sum(1 for result in results if result["status"] == "pass")
    total = len(results)
    status = "pass" if passed == total else "fail"
    return ConformanceStep(
        "negative-conformance-suite",
        "Negative conformance suite",
        status,
        detail=f"{passed}/{total} negative cases passed",
        metadata={"passed": passed, "total": total, "cases": results},
    )


def _run_negative_case(case: dict[str, Any]) -> dict[str, Any]:
    with TemporaryDirectory(prefix="skills-orchestrator-negative-") as temp_dir:
        root = Path(temp_dir)
        skills_dir = root / "skills"
        skills_dir.mkdir()
        for index, body in enumerate(case["skills"], start=1):
            (skills_dir / f"skill-{index}.md").write_text(body, encoding="utf-8")
        config_dir = root / "config"
        config_dir.mkdir()
        config = config_dir / "skills.yaml"
        config.write_text(
            f"""
version: "2.0"
skill_dirs:
  - {skills_dir}
zones:
  - id: default
    name: Default
    load_policy: free
    rules: []
""",
            encoding="utf-8",
        )
        report = run_check(str(config), policy_packs=case["policy_packs"])
        actual_rules = {diagnostic.rule_id for diagnostic in report.diagnostics}
        expected_rules = set(case["expected_rules"])
        missing_rules = sorted(expected_rules - actual_rules)
        return {
            "id": case["id"],
            "status": "pass" if not missing_rules else "fail",
            "expected_rules": sorted(expected_rules),
            "actual_rules": sorted(actual_rules),
            "missing_rules": missing_rules,
        }


def _evidence_ledger_step(bundle: dict[str, Any]) -> ConformanceStep:
    ledger = bundle.get("ledger") or {}
    artifact_hashes = ledger.get("artifact_hashes") or {}
    bundle_hash = str(ledger.get("bundle_hash", ""))
    expected_labels = set(bundle.get("files", {}))
    missing_labels = sorted(expected_labels - set(artifact_hashes))
    invalid_hashes = [
        label
        for label, value in artifact_hashes.items()
        if not isinstance(value, dict)
        or value.get("alg") != "SHA-256"
        or not _sha256_hex(str(value.get("value", "")))
    ]
    if not _sha256_hex(bundle_hash):
        return ConformanceStep(
            "evidence-ledger",
            "Evidence ledger contract",
            "fail",
            detail="missing or invalid bundle_hash",
        )
    if missing_labels or invalid_hashes:
        return ConformanceStep(
            "evidence-ledger",
            "Evidence ledger contract",
            "fail",
            detail="missing or invalid artifact hashes",
            metadata={
                "missing_labels": missing_labels,
                "invalid_hashes": sorted(invalid_hashes),
            },
        )
    return ConformanceStep(
        "evidence-ledger",
        "Evidence ledger contract",
        "pass",
        detail=f"{len(artifact_hashes)} artifact hashes",
        metadata={"artifact_hashes": len(artifact_hashes)},
    )


def _sha256_hex(value: str) -> bool:
    return len(value) == 64 and all(char in "0123456789abcdef" for char in value)


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
