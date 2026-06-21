import json

from click.testing import CliRunner

from skills_orchestrator.checker import run_check
from skills_orchestrator.diagnostic import DiagnosticSeverity
from skills_orchestrator.main import cli


def _workspace(tmp_path, frontmatter_extra: str = ""):
    tmp_path.mkdir(parents=True, exist_ok=True)
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


def test_engineering_grade_pack_requires_review_window(tmp_path):
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

    report = run_check(str(config), policy_packs=["builtin/engineering-grade"])

    rule_ids = {diagnostic.rule_id for diagnostic in report.diagnostics}
    assert "SO014" in rule_ids
    assert "SO008" not in rule_ids


def test_engineering_grade_pack_passes_complete_metadata(tmp_path):
    config = _workspace(
        tmp_path,
        frontmatter_extra=(
            "owner: platform-team\n"
            "source: https://example.com/skills/required\n"
            "version: 2026.06\n"
            "lifecycle: active\n"
            "approvers: [staff-engineering]\n"
            "reviewed_at: 2026-06-21\n"
            "expires_at: 2999-01-01\n"
        ),
    )

    report = run_check(str(config), policy_packs=["builtin/engineering-grade"])

    assert report.diagnostics == []


def test_engineering_grade_pack_rejects_invalid_and_expired_dates(tmp_path):
    invalid_config = _workspace(
        tmp_path / "invalid",
        frontmatter_extra=(
            "owner: platform-team\n"
            "source: internal\n"
            "version: 1.0.0\n"
            "lifecycle: active\n"
            "approvers: [staff-engineering]\n"
            "reviewed_at: yesterday\n"
            "expires_at: 2999-01-01\n"
        ),
    )
    expired_config = _workspace(
        tmp_path / "expired",
        frontmatter_extra=(
            "owner: platform-team\n"
            "source: internal\n"
            "version: 1.0.0\n"
            "lifecycle: active\n"
            "approvers: [staff-engineering]\n"
            "reviewed_at: 2000-01-01\n"
            "expires_at: 2000-01-02\n"
        ),
    )

    invalid = run_check(str(invalid_config), policy_packs=["builtin/engineering-grade"])
    expired = run_check(str(expired_config), policy_packs=["builtin/engineering-grade"])

    assert [diagnostic.rule_id for diagnostic in invalid.diagnostics] == ["SO015"]
    assert [diagnostic.rule_id for diagnostic in expired.diagnostics] == ["SO016"]


def test_engineering_grade_pack_requires_dash_separated_iso_dates(tmp_path):
    config = _workspace(
        tmp_path,
        frontmatter_extra=(
            "owner: platform-team\n"
            "source: internal\n"
            "version: 1.0.0\n"
            "lifecycle: active\n"
            "approvers: [staff-engineering]\n"
            "reviewed_at: 20260621\n"
            "expires_at: 29990101\n"
        ),
    )

    report = run_check(str(config), policy_packs=["builtin/engineering-grade"])

    assert [diagnostic.rule_id for diagnostic in report.diagnostics] == ["SO015"]


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


def test_declarative_policy_pack_reports_custom_required_field(tmp_path):
    config = _workspace(
        tmp_path,
        frontmatter_extra=(
            "owner: platform-team\n"
            "source: internal\n"
            "version: 1.0.0\n"
            "lifecycle: active\n"
            "approvers: [staff-engineering]\n"
        ),
    )
    pack = tmp_path / "policy-pack.yaml"
    pack.write_text(
        """
schema_version: skills-orchestrator.policy-pack.v1
id: org/enterprise
name: Enterprise
rules:
  - id: require-expiry
    severity: error
    required_fields: [expires_at]
""",
        encoding="utf-8",
    )

    report = run_check(str(config), policy_packs=[str(pack)])

    assert len(report.diagnostics) == 1
    diagnostic = report.diagnostics[0]
    assert diagnostic.rule_id == "SO017"
    assert diagnostic.severity == DiagnosticSeverity.ERROR
    assert diagnostic.metadata["declarative_rule"] == "require-expiry"


def test_check_cli_declarative_policy_pack_json(tmp_path):
    config = _workspace(
        tmp_path,
        frontmatter_extra=(
            "owner: platform-team\n"
            "source: internal\n"
            "version: 1.0.0\n"
            "lifecycle: active\n"
            "approvers: [staff-engineering]\n"
        ),
    )
    pack = tmp_path / "policy-pack.yaml"
    pack.write_text(
        """
schema_version: skills-orchestrator.policy-pack.v1
id: org/allowed-lifecycle
rules:
  - id: no-active
    severity: warning
    allowed_values:
      - field: lifecycle
        values: [beta]
""",
        encoding="utf-8",
    )
    runner = CliRunner()

    result = runner.invoke(
        cli,
        [
            "check",
            "--config",
            str(config),
            "--policy-pack",
            str(pack),
            "--format",
            "json",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    diagnostic = payload["diagnostics"][0]
    assert diagnostic["rule_id"] == "SO017"
    assert diagnostic["metadata"]["policy_pack"] == "org/allowed-lifecycle"


def test_declarative_policy_pack_rejects_allowed_values_on_list_fields(tmp_path):
    config = _workspace(tmp_path)
    pack = tmp_path / "policy-pack.yaml"
    pack.write_text(
        """
schema_version: skills-orchestrator.policy-pack.v1
id: org/bad-allowed-field
rules:
  - id: no-list-allowed-values
    allowed_values:
      - field: tags
        values: [review]
""",
        encoding="utf-8",
    )
    runner = CliRunner()

    result = runner.invoke(
        cli,
        ["check", "--config", str(config), "--policy-pack", str(pack)],
    )

    assert result.exit_code == 1
    assert "Invalid policy pack" in result.output
