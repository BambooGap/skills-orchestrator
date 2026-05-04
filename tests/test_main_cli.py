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


def test_validate_error_path(workspace):
    runner = CliRunner()
    result = runner.invoke(
        cli, ["validate", "--config", workspace["config"], "--zone", "not-exist"]
    )
    assert result.exit_code != 0
    assert "不存在" in result.output


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
