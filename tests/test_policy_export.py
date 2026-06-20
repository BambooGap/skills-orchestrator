import json

import pytest
from click.testing import CliRunner

from skills_orchestrator.compiler import Parser, Resolver
from skills_orchestrator.main import cli
from skills_orchestrator.policy import build_opa_input, build_rego_test


def _policy_workspace(tmp_path):
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    (skills_dir / "alpha.md").write_text(
        "---\n"
        "id: alpha\n"
        "name: Alpha\n"
        "summary: Alpha skill\n"
        "load_policy: require\n"
        "priority: 20\n"
        "conflict_with: [beta]\n"
        "owner: platform-team\n"
        "source: internal://alpha\n"
        "version: 1.0.0\n"
        "lifecycle: active\n"
        "---\n"
        "# Alpha\n",
        encoding="utf-8",
    )
    (skills_dir / "beta.md").write_text(
        "---\nid: beta\nname: Beta\nsummary: Beta skill\npriority: 10\n---\n# Beta\n",
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
  - id: enterprise
    name: Enterprise
    load_policy: require
    rules: []
""",
        encoding="utf-8",
    )
    return config


def test_build_opa_input_exports_resolver_facts(tmp_path):
    config = _policy_workspace(tmp_path)
    cfg = Parser(str(config)).parse()
    resolved = Resolver(cfg).resolve()

    payload = build_opa_input(cfg, resolved)

    assert payload["schema_version"] == "1.0"
    assert payload["resolution"]["forced"] == ["alpha"]
    assert payload["resolution"]["passive"] == []
    assert payload["resolution"]["blocked"] == ["beta"]
    alpha = next(skill for skill in payload["skills"] if skill["id"] == "alpha")
    beta = next(skill for skill in payload["skills"] if skill["id"] == "beta")
    assert alpha["effective_load_policy"] == "require"
    assert alpha["governance"]["owner"] == "platform-team"
    assert beta["status"] == "blocked"
    assert beta["block_reason"]


def test_build_rego_test_embeds_fixture_and_checks_resolution(tmp_path):
    config = _policy_workspace(tmp_path)
    cfg = Parser(str(config)).parse()
    resolved = Resolver(cfg).resolve()
    payload = build_opa_input(cfg, resolved)

    rego = build_rego_test(payload, package="skills_orchestrator_generated_test")

    assert rego.startswith("package skills_orchestrator_generated_test\n")
    assert "fixture :=" in rego
    assert "test_export_matches_resolver_resolution if" in rego
    assert '"blocked": [\n      "beta"\n    ]' in rego


def test_build_rego_test_rejects_invalid_package(tmp_path):
    config = _policy_workspace(tmp_path)
    cfg = Parser(str(config)).parse()
    resolved = Resolver(cfg).resolve()
    payload = build_opa_input(cfg, resolved)

    with pytest.raises(ValueError, match="Rego package"):
        build_rego_test(payload, package="bad-name")


def test_policy_export_cli_outputs_json_and_rego(tmp_path):
    config = _policy_workspace(tmp_path)
    runner = CliRunner()

    json_result = runner.invoke(
        cli, ["policy", "export", "--config", str(config), "--format", "opa-input"]
    )
    assert json_result.exit_code == 0
    payload = json.loads(json_result.output)
    assert payload["resolution"]["blocked"] == ["beta"]

    rego_result = runner.invoke(
        cli,
        [
            "policy",
            "export",
            "--config",
            str(config),
            "--format",
            "rego-test",
            "--package",
            "skills_orchestrator_policy_test",
        ],
    )
    assert rego_result.exit_code == 0
    assert "package skills_orchestrator_policy_test" in rego_result.output


def test_policy_export_cli_unknown_zone_exits_nonzero(tmp_path):
    config = _policy_workspace(tmp_path)
    runner = CliRunner()

    result = runner.invoke(cli, ["policy", "export", "--config", str(config), "--zone", "missing"])

    assert result.exit_code == 1
    assert "Zone 'missing' 不存在" in result.output
