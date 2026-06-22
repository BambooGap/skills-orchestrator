"""Evidence bundle export for CI, audit, and commercial handoff."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from skills_orchestrator.adapters.inspect import inspect_adapters
from skills_orchestrator.checker import run_check
from skills_orchestrator.compiler import Parser, Resolver
from skills_orchestrator.compiler.instruction_manifest import build_instruction_manifest
from skills_orchestrator.doctor import run_doctor
from skills_orchestrator.formatters import format_diagnostics_json, format_diagnostics_sarif
from skills_orchestrator.formatters.manifest import format_instruction_manifest_json
from skills_orchestrator.org_registry import build_registry
from skills_orchestrator.policy.exporter import build_opa_input, build_rego_test
from skills_orchestrator.supply_chain import build_python_package_sbom, format_sbom_json


def export_evidence_bundle(
    config_path: str,
    out_dir: str,
    *,
    zone_id: str | None = None,
    policy_packs: tuple[str, ...] | list[str] = (),
    check_lock: str | None = None,
    agents_md: str = "AGENTS.md",
    previous_bundle_hash: str | None = None,
) -> dict[str, Any]:
    """Write a local evidence bundle and return its manifest."""
    output = Path(out_dir)
    output.mkdir(parents=True, exist_ok=True)
    root = _workspace_root(config_path)

    parser = Parser(config_path)
    cfg = parser.parse()
    target_zone = None
    if zone_id:
        target_zone = next((zone for zone in cfg.zones if zone.id == zone_id), None)
        if target_zone is None:
            raise ValueError(f"Zone '{zone_id}' does not exist")
    resolved = Resolver(cfg).resolve(target_zone)

    check_report = run_check(
        config_path,
        zone_id=zone_id,
        check_lock=check_lock,
        policy_packs=policy_packs,
    )
    manifest = build_instruction_manifest(config_path, cfg, resolved)
    opa_input = build_opa_input(cfg, resolved)
    doctor = run_doctor(
        config_path,
        zone_id=zone_id,
        policy_packs=policy_packs,
        check_lock=check_lock,
        agents_md=agents_md,
    )
    registry = build_registry([config_path], zone_id=zone_id)
    adapter_inspect = inspect_adapters(root)
    package_sbom = build_python_package_sbom()

    files = {
        "check_json": _write(output / "check.json", format_diagnostics_json(check_report)),
        "check_sarif": _write(output / "check.sarif", format_diagnostics_sarif(check_report)),
        "instruction_manifest": _write(
            output / "instruction-manifest.json", format_instruction_manifest_json(manifest)
        ),
        "opa_input": _write(
            output / "policy-opa-input.json",
            json.dumps(opa_input, ensure_ascii=False, indent=2) + "\n",
        ),
        "rego_test": _write(output / "policy-proof.rego", build_rego_test(opa_input)),
        "doctor": _write(
            output / "doctor.json",
            json.dumps(doctor, ensure_ascii=False, indent=2) + "\n",
        ),
        "registry": _write(
            output / "skill-registry.json",
            json.dumps(registry, ensure_ascii=False, indent=2) + "\n",
        ),
        "adapter_inspect": _write(
            output / "adapter-inspect.json",
            json.dumps(adapter_inspect, ensure_ascii=False, indent=2) + "\n",
        ),
        "package_sbom": _write(output / "package-sbom.cdx.json", format_sbom_json(package_sbom)),
    }
    bundle = {
        "schema_version": "skills-orchestrator.evidence-bundle.v1",
        "config": config_path,
        "zone": zone_id or manifest["zone"]["id"],
        "policy_packs": list(policy_packs),
        "files": files,
        "ledger": {
            "artifact_hashes": _artifact_hashes(files),
            "previous_bundle_hash": previous_bundle_hash or "",
            "bundle_hash": "",
        },
    }
    bundle["ledger"]["bundle_hash"] = _bundle_hash(bundle)
    _write(
        output / "evidence-manifest.json",
        json.dumps(bundle, ensure_ascii=False, indent=2) + "\n",
    )
    return bundle


def _workspace_root(config_path: str) -> Path:
    config = Path(config_path).expanduser()
    if not config.is_absolute():
        config = (Path.cwd() / config).resolve()
    else:
        config = config.resolve()
    return config.parent.parent if config.parent.name == "config" else config.parent


def _write(path: Path, content: str) -> str:
    path.write_text(content, encoding="utf-8")
    return str(path)


def _artifact_hashes(files: dict[str, str]) -> dict[str, dict[str, str]]:
    hashes: dict[str, dict[str, str]] = {}
    for label, path_text in sorted(files.items()):
        path = Path(path_text)
        hashes[label] = {
            "alg": "SHA-256",
            "value": hashlib.sha256(path.read_bytes()).hexdigest(),
            "path": path_text,
        }
    return hashes


def _bundle_hash(bundle: dict[str, Any]) -> str:
    payload = json.loads(json.dumps(bundle, ensure_ascii=False, sort_keys=True))
    payload["ledger"]["bundle_hash"] = ""
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
