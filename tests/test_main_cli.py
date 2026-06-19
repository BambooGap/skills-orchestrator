import json

import pytest
from click.testing import CliRunner

from skills_orchestrator.main import cli


@pytest.fixture
def workspace(tmp_path):
    # Create skills/test.md
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    skill_file = skills_dir / "test-skill.md"
    skill_file.write_text(
        "---\n"
        "id: test-skill\n"
        "name: Test Skill\n"
        "summary: Sum\n"
        "priority: 10\n"
        "load_policy: free\n"
        "zones: [default]\n"
        "---\n"
        "# Content\n",
        encoding="utf-8",
    )

    # Create config/skills.yaml
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    config_yaml = config_dir / "skills.yaml"
    config_yaml.write_text(
        f"""
version: "2.0"
skill_dirs:
  - {skills_dir.resolve()}
zones:
  - id: default
    name: 默认区
    load_policy: free
    rules: []
""",
        encoding="utf-8",
    )

    # Create config/pipelines/test-pipeline.yaml
    pipelines_dir = config_dir / "pipelines"
    pipelines_dir.mkdir()
    pipeline_file = pipelines_dir / "test-pipeline.yaml"
    pipeline_file.write_text(
        """
id: test-pipeline
name: Test Pipeline
steps:
  - id: step1
    skill: test-skill
""",
        encoding="utf-8",
    )

    return {
        "root": tmp_path,
        "config": str(config_yaml.resolve()),
        "pipelines_dir": str(pipelines_dir.resolve()),
    }


def test_build_happy_path(workspace):
    runner = CliRunner()
    output_md = workspace["root"] / "AGENTS.md"
    result = runner.invoke(
        cli, ["build", "--config", workspace["config"], "--output", str(output_md)]
    )
    assert result.exit_code == 0
    assert "解析完成" in result.output
    assert output_md.exists()


def test_build_error_path(workspace):
    runner = CliRunner()
    result = runner.invoke(cli, ["build", "--config", "not-exist.yaml"])
    assert result.exit_code != 0
    assert "✗" in result.output  # Error indicator


def test_validate_happy_path(workspace):
    runner = CliRunner()
    result = runner.invoke(cli, ["validate", "--config", workspace["config"]])
    assert result.exit_code == 0
    assert "配置验证通过" in result.output


def test_validate_json_format_happy_path(workspace):
    runner = CliRunner()
    result = runner.invoke(cli, ["validate", "--config", workspace["config"], "--format", "json"])
    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["tool"]["name"] == "skills-orchestrator"
    assert payload["summary"]["skills"] == 1


def test_validate_sarif_format_reports_fatal_errors(workspace):
    bad_config = workspace["root"] / "config" / "bad-skills.yaml"
    bad_config.write_text(
        """
version: "2.0"
skill_dirs:
  - missing-skills
zones:
  - id: default
    name: Default
    load_policy: free
    rules: []
""",
        encoding="utf-8",
    )

    runner = CliRunner()
    result = runner.invoke(cli, ["validate", "--config", str(bad_config), "--format", "sarif"])

    assert result.exit_code == 1
    payload = json.loads(result.output)
    assert payload["runs"][0]["results"][0]["ruleId"] == "SO000"


def test_validate_error_path(workspace):
    runner = CliRunner()
    result = runner.invoke(
        cli, ["validate", "--config", workspace["config"], "--zone", "not-exist"]
    )
    assert result.exit_code != 0
    assert "不存在" in result.output


def test_check_json_format_happy_path(workspace):
    runner = CliRunner()
    result = runner.invoke(cli, ["check", "--config", workspace["config"], "--format", "json"])
    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["schema_version"] == "1.0"
    assert payload["summary"]["skills"] == 1


def test_check_json_format_reports_fatal_errors(workspace):
    bad_config = workspace["root"] / "config" / "bad-skills.yaml"
    bad_config.write_text(
        """
version: "2.0"
skill_dirs:
  - missing-skills
zones:
  - id: default
    name: Default
    load_policy: free
    rules: []
""",
        encoding="utf-8",
    )

    runner = CliRunner()
    result = runner.invoke(cli, ["check", "--config", str(bad_config), "--format", "json"])

    assert result.exit_code == 1
    payload = json.loads(result.output)
    assert payload["diagnostics"][0]["rule_id"] == "SO000"


def test_check_sarif_format_happy_path(workspace):
    runner = CliRunner()
    result = runner.invoke(cli, ["check", "--config", workspace["config"], "--format", "sarif"])
    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["version"] == "2.1.0"
    assert payload["runs"][0]["tool"]["driver"]["name"] == "skills-orchestrator"


def test_check_lock_drift_exits_nonzero_by_default(workspace):
    runner = CliRunner()
    output_md = workspace["root"] / "AGENTS.md"
    lock_path = workspace["root"] / "skills.lock.json"
    build_result = runner.invoke(
        cli,
        [
            "build",
            "--config",
            workspace["config"],
            "--output",
            str(output_md),
            "--lock",
        ],
    )
    assert build_result.exit_code == 0

    skill_path = workspace["root"] / "skills" / "test-skill.md"
    skill_path.write_text(skill_path.read_text(encoding="utf-8") + "\nExtra content\n")

    result = runner.invoke(
        cli,
        ["check", "--config", workspace["config"], "--check-lock", str(lock_path)],
    )
    assert result.exit_code == 1
    assert "SO007" in result.output


def test_check_lock_drift_fail_on_never_allows_zero(workspace):
    runner = CliRunner()
    output_md = workspace["root"] / "AGENTS.md"
    lock_path = workspace["root"] / "skills.lock.json"
    build_result = runner.invoke(
        cli,
        [
            "build",
            "--config",
            workspace["config"],
            "--output",
            str(output_md),
            "--lock",
        ],
    )
    assert build_result.exit_code == 0

    skill_path = workspace["root"] / "skills" / "test-skill.md"
    skill_path.write_text(skill_path.read_text(encoding="utf-8") + "\nExtra content\n")

    result = runner.invoke(
        cli,
        [
            "check",
            "--config",
            workspace["config"],
            "--check-lock",
            str(lock_path),
            "--fail-on",
            "never",
        ],
    )
    assert result.exit_code == 0
    assert "SO007" in result.output


def test_check_fail_on_warning_exits_for_warning(workspace):
    skill_path = workspace["root"] / "skills" / "test-skill.md"
    skill_path.write_text(
        "---\n"
        "id: test-skill\n"
        "name: Test Skill\n"
        "summary: Sum\n"
        "priority: 10\n"
        "load_policy: free\n"
        "zones: [default]\n"
        "conflict_with: [other-skill]\n"
        "---\n"
        "# Content\n",
        encoding="utf-8",
    )
    other_skill = workspace["root"] / "skills" / "other-skill.md"
    other_skill.write_text(
        "---\nid: other-skill\nname: Other Skill\nsummary: Other\nzones: [default]\n---\n# Other\n",
        encoding="utf-8",
    )

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["check", "--config", workspace["config"], "--fail-on", "warning"],
    )
    assert result.exit_code == 1
    assert "SO004" in result.output


def test_pipeline_list_runs_text_and_json(workspace, monkeypatch):
    from skills_orchestrator.pipeline.models import RunState
    from skills_orchestrator.pipeline.store import RunStateStore

    monkeypatch.setenv("HOME", str(workspace["root"]))
    state = RunState(pipeline_id="test-pipeline", run_id="run1")
    state.advance_to("step1")
    RunStateStore().save(state)

    runner = CliRunner()
    text_result = runner.invoke(cli, ["pipeline", "list-runs"])
    assert text_result.exit_code == 0
    assert "test-pipeline" in text_result.output
    assert "run1" in text_result.output

    json_result = runner.invoke(cli, ["pipeline", "list-runs", "test-pipeline", "--json"])
    assert json_result.exit_code == 0
    payload = json.loads(json_result.output)
    assert payload["runs"][0]["pipeline_id"] == "test-pipeline"
    assert payload["runs"][0]["run_id"] == "run1"


def test_status_happy_path(workspace):
    runner = CliRunner()
    result = runner.invoke(cli, ["status", "--config", workspace["config"]])
    assert result.exit_code == 0
    assert "Passive Skills" in result.output
    assert "test-skill" in result.output


def test_status_error_path(workspace):
    runner = CliRunner()
    result = runner.invoke(cli, ["status", "--config", workspace["config"], "--zone", "not-exist"])
    assert result.exit_code != 0
    assert "不存在" in result.output


def test_inspect_happy_path(workspace):
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "inspect",
            "--workdir",
            str(workspace["root"]),
            "--config",
            workspace["config"],
        ],
    )
    assert result.exit_code == 0
    assert "命中 Zone" in result.output
    assert "default" in result.output


def test_inspect_error_path(workspace):
    runner = CliRunner()
    result = runner.invoke(cli, ["inspect", "--config", "not-exist.yaml"])
    assert result.exit_code != 0
    assert "✗" in result.output


def test_sync_dry_run_happy_path(workspace):
    runner = CliRunner()
    result = runner.invoke(cli, ["sync", "agents-md", "--config", workspace["config"], "--dry-run"])
    assert result.exit_code == 0
    assert "[dry-run]" in result.output
    assert "test-skill" in result.output


def test_sync_error_path(workspace):
    runner = CliRunner()
    # Provide an invalid zone to trigger error
    result = runner.invoke(
        cli,
        [
            "sync",
            "agents-md",
            "--config",
            workspace["config"],
            "--zone",
            "not-exist",
            "--dry-run",
        ],
    )
    assert result.exit_code != 0
    assert "不存在" in result.output


def test_pipeline_list_happy_path(workspace):
    runner = CliRunner()
    result = runner.invoke(cli, ["pipeline", "list", "--config", workspace["config"]])
    assert result.exit_code == 0
    assert "test-pipeline" in result.output


def test_pipeline_list_compact(workspace):
    runner = CliRunner()
    result = runner.invoke(cli, ["pipeline", "list", "--config", workspace["config"], "--compact"])
    assert result.exit_code == 0
    assert "可用 Pipeline" in result.output
    assert "test-pipeline" in result.output


def test_pipeline_list_detail(workspace):
    runner = CliRunner()
    result = runner.invoke(cli, ["pipeline", "list", "--config", workspace["config"], "--detail"])
    assert result.exit_code == 0
    assert "📋 可用的 Pipeline 模板" in result.output
    assert "test-pipeline" in result.output


def test_pipeline_start_missing(workspace):
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "pipeline",
            "start",
            "non-existent-pipeline",
            "--config",
            workspace["config"],
        ],
    )
    assert result.exit_code != 0
    assert "不存在或加载失败" in result.output
