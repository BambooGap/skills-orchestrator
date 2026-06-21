import json

from click.testing import CliRunner

from skills_orchestrator.checker import run_check
from skills_orchestrator.diagnostic import DiagnosticSeverity
from skills_orchestrator.main import cli


def _workspace(tmp_path, frontmatter_extra: str = ""):
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    (skills_dir / "required.md").write_text(
        "---\n"
        "id: required\n"
        "name: Required\n"
        "summary: Required skill\n"
        "load_policy: require\n"
        f"{frontmatter_extra}"
        "---\n"
        "# Required\n",
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
""",
        encoding="utf-8",
    )
    return config


def test_team_standard_policy_pack_reports_missing_governance(tmp_path):
    config = _workspace(tmp_path)

    report = run_check(str(config), policy_packs=["builtin/team-standard"])

    rule_ids = {diagnostic.rule_id for diagnostic in report.diagnostics}
    assert {"SO008", "SO009", "SO010", "SO012"}.issubset(rule_ids)
    assert all(diagnostic.severity != DiagnosticSeverity.ERROR for diagnostic in report.diagnostics)


def test_team_standard_policy_pack_passes_complete_metadata(tmp_path):
    config = _workspace(
        tmp_path,
        frontmatter_extra=(
            "owner: platform-team\n"
            "source: https://example.com/skills/required\n"
            "version: 2026.06\n"
            "lifecycle: active\n"
            "approvers: [staff-engineering]\n"
        ),
    )

    report = run_check(str(config), policy_packs=["builtin/team-standard"])

    assert report.diagnostics == []


def test_team_standard_policy_pack_rejects_unknown_lifecycle(tmp_path):
    config = _workspace(
        tmp_path,
        frontmatter_extra=(
            "owner: platform-team\n"
            "source: internal\n"
            "version: 1.0.0\n"
            "lifecycle: archived\n"
            "approvers: [staff-engineering]\n"
        ),
    )

    report = run_check(str(config), policy_packs=["builtin/team-standard"])

    invalid = [diagnostic for diagnostic in report.diagnostics if diagnostic.rule_id == "SO011"]
    assert len(invalid) == 1
    assert invalid[0].severity == DiagnosticSeverity.ERROR


def test_team_standard_policy_pack_treats_null_governance_as_missing(tmp_path):
    config = _workspace(
        tmp_path,
        frontmatter_extra=(
            "owner:\nsource:\nversion:\nlifecycle:\napprovers: [staff-engineering]\n"
        ),
    )

    report = run_check(str(config), policy_packs=["builtin/team-standard"])

    by_rule = {diagnostic.rule_id: diagnostic for diagnostic in report.diagnostics}
    assert {"SO008", "SO009", "SO010", "SO011"}.issubset(by_rule)
    assert by_rule["SO011"].severity == DiagnosticSeverity.ERROR


def test_check_cli_policy_pack_json(tmp_path):
    config = _workspace(tmp_path)
    runner = CliRunner()

    result = runner.invoke(
        cli,
        [
            "check",
            "--config",
            str(config),
            "--policy-pack",
            "builtin/team-standard",
            "--format",
            "json",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert "SO008" in {diagnostic["rule_id"] for diagnostic in payload["diagnostics"]}


def test_check_cli_unknown_policy_pack_exits_nonzero(tmp_path):
    config = _workspace(tmp_path)
    runner = CliRunner()

    result = runner.invoke(
        cli,
        ["check", "--config", str(config), "--policy-pack", "unknown/pack"],
    )

    assert result.exit_code == 1
    assert "Unknown policy pack" in result.output
