import json

from click.testing import CliRunner

from skills_orchestrator.compiler import Parser, Resolver, build_instruction_manifest
from skills_orchestrator.formatters import (
    format_instruction_manifest_cyclonedx,
    format_instruction_manifest_json,
)
from skills_orchestrator.main import cli


def _manifest_workspace(tmp_path):
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    (skills_dir / "base.md").write_text(
        "---\nid: base\nname: Base Skill\nsummary: Shared guidance\ntags: [base]\n---\n# Base\n",
        encoding="utf-8",
    )
    (skills_dir / "child.md").write_text(
        "---\n"
        "id: child\n"
        "name: Child Skill\n"
        "summary: Child guidance\n"
        "base: base\n"
        "owner: platform-team\n"
        "source: internal://child\n"
        "version: 1.0.0\n"
        "lifecycle: active\n"
        "approvers: [staff-engineering]\n"
        "tags: [child]\n"
        "---\n"
        "# Child\n",
        encoding="utf-8",
    )
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    config = config_dir / "skills.yaml"
    config.write_text(
        f"""
version: "2.0"
skill_dirs:
  - {skills_dir.resolve()}
zones:
  - id: default
    name: Default
    load_policy: free
    rules: []
combos:
  - id: delivery
    name: Delivery
    members: [base, child]
    description: Delivery combo
""",
        encoding="utf-8",
    )
    return config


def test_build_instruction_manifest_records_full_hash_and_base(tmp_path):
    config = _manifest_workspace(tmp_path)
    cfg = Parser(str(config)).parse()
    resolved = Resolver(cfg).resolve()

    manifest = build_instruction_manifest(str(config), cfg, resolved)

    assert manifest["schema_version"] == "1.0"
    assert manifest["summary"] == {
        "total": 2,
        "forced": 0,
        "passive": 2,
        "blocked": 0,
        "combos": 1,
    }
    child = next(skill for skill in manifest["skills"] if skill["id"] == "child")
    assert child["status"] == "passive"
    assert child["base"] == "base"
    assert child["content_hash"]["alg"] == "SHA-256"
    assert len(child["content_hash"]["value"]) == 64
    assert child["size_bytes"] > 0
    assert child["missing_file"] is False
    assert child["governance"]["owner"] == "platform-team"
    assert child["governance"]["approvers"] == ["staff-engineering"]


def test_instruction_manifest_cyclonedx_maps_skills_and_dependencies(tmp_path):
    config = _manifest_workspace(tmp_path)
    cfg = Parser(str(config)).parse()
    resolved = Resolver(cfg).resolve()
    manifest = build_instruction_manifest(str(config), cfg, resolved)

    bom = json.loads(format_instruction_manifest_cyclonedx(manifest))

    assert bom["bomFormat"] == "CycloneDX"
    assert bom["specVersion"] == "1.7"
    child = next(
        component for component in bom["components"] if component["bom-ref"] == "skill:child"
    )
    assert child["type"] == "data"
    assert len(child["hashes"][0]["content"]) == 64
    assert {"ref": "skill:child", "dependsOn": ["skill:base"]} in bom["dependencies"]
    assert any(prop["name"] == "skills-orchestrator:governance" for prop in child["properties"])
    assert any(prop["name"] == "skills-orchestrator:experimental" for prop in bom["properties"])


def test_manifest_json_formatter_returns_valid_json(tmp_path):
    config = _manifest_workspace(tmp_path)
    cfg = Parser(str(config)).parse()
    resolved = Resolver(cfg).resolve()
    manifest = build_instruction_manifest(str(config), cfg, resolved)

    payload = json.loads(format_instruction_manifest_json(manifest))

    assert payload["tool"]["name"] == "skills-orchestrator"
    assert payload["combos"][0]["id"] == "delivery"


def test_manifest_cli_stdout_and_output_file(tmp_path):
    config = _manifest_workspace(tmp_path)
    output = tmp_path / "instruction-manifest.cdx.json"
    runner = CliRunner()

    stdout_result = runner.invoke(cli, ["manifest", "--config", str(config), "--format", "json"])
    assert stdout_result.exit_code == 0
    payload = json.loads(stdout_result.output)
    assert payload["summary"]["total"] == 2

    file_result = runner.invoke(
        cli,
        [
            "manifest",
            "--config",
            str(config),
            "--format",
            "cyclonedx",
            "--output",
            str(output),
        ],
    )
    assert file_result.exit_code == 0
    assert file_result.output == ""
    assert json.loads(output.read_text(encoding="utf-8"))["bomFormat"] == "CycloneDX"


def test_manifest_cli_include_diagnostics(tmp_path):
    config = _manifest_workspace(tmp_path)
    runner = CliRunner()

    result = runner.invoke(cli, ["manifest", "--config", str(config), "--include-diagnostics"])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["diagnostics"]["summary"]["skills"] == 2
