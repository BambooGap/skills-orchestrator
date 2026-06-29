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


def test_check_reports_invalid_frontmatter_load_policy_with_skill_location(workspace):
    skill_path = workspace["root"] / "skills" / "test-skill.md"
    skill_path.write_text(
        skill_path.read_text(encoding="utf-8").replace(
            "load_policy: free", "load_policy: bogus-policy"
        ),
        encoding="utf-8",
    )

    runner = CliRunner()
    json_result = runner.invoke(cli, ["check", "--config", workspace["config"], "--format", "json"])
    text_result = runner.invoke(cli, ["check", "--config", workspace["config"], "--format", "text"])
    sarif_result = runner.invoke(
        cli, ["check", "--config", workspace["config"], "--format", "sarif"]
    )

    assert json_result.exit_code == 1
    json_payload = json.loads(json_result.output)
    diagnostic = json_payload["diagnostics"][0]
    assert diagnostic["rule_id"] == "SO013"
    assert diagnostic["file"] == "skills/test-skill.md"
    assert diagnostic["line"] == 6
    assert diagnostic["skill_id"] == "test-skill"
    assert "bogus-policy" in diagnostic["message"]

    assert text_result.exit_code == 1
    assert "SO013" in text_result.output
    assert "skills/test-skill.md:6" in text_result.output

    assert sarif_result.exit_code == 1
    sarif_payload = json.loads(sarif_result.output)
    result = sarif_payload["runs"][0]["results"][0]
    assert result["ruleId"] == "SO013"
    location = result["locations"][0]["physicalLocation"]
    assert location["artifactLocation"]["uri"] == "skills/test-skill.md"
    assert location["region"]["startLine"] == 6


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


def test_usage_report_json_reads_audit_events(tmp_path):
    audit_dir = tmp_path / "audit"
    audit_dir.mkdir()
    (audit_dir / "events.jsonl").write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "event": "prepare_context_decision",
                        "tool": "prepare_context",
                        "outcome": "decision",
                        "active_skill_ids": ["team-review"],
                    }
                ),
                json.dumps(
                    {
                        "event": "mcp_tool_call",
                        "tool": "prepare_context",
                        "outcome": "ok",
                    }
                ),
            ]
        ),
        encoding="utf-8",
    )

    runner = CliRunner()
    result = runner.invoke(cli, ["usage", "report", "--audit-dir", str(audit_dir), "--json"])
    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["events"] == 2
    assert payload["tools"]["prepare_context"] == 1
    assert payload["top_active_skills"]["team-review"] == 1


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


def test_pipeline_start_invalid_definition_exits_nonzero(workspace):
    invalid_pipeline = workspace["root"] / "config" / "pipelines" / "invalid-pipeline.yaml"
    invalid_pipeline.write_text(
        """
id: invalid-pipeline
name: Invalid Pipeline
steps:
  - id: first
    skill: test-skill
  - id: unreachable
    skill: test-skill
""",
        encoding="utf-8",
    )
    runner = CliRunner()

    result = runner.invoke(
        cli,
        [
            "pipeline",
            "start",
            "invalid-pipeline",
            "--config",
            workspace["config"],
        ],
    )

    assert result.exit_code != 0
    assert "定义无效" in result.output
    assert "不可达" in result.output


def test_pipeline_start_and_advance_do_not_require_mcp_runtime(workspace, monkeypatch):
    import builtins

    monkeypatch.setenv("HOME", str(workspace["root"]))
    real_import = builtins.__import__

    def guarded_import(name, globals=None, locals=None, fromlist=(), level=0):
        if level == 0 and (
            name == "mcp" or name.startswith("mcp.") or name == "skills_orchestrator.mcp.tools"
        ):
            raise ModuleNotFoundError("No module named 'mcp'", name="mcp")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", guarded_import)
    runner = CliRunner()

    start_result = runner.invoke(
        cli,
        [
            "pipeline",
            "start",
            "test-pipeline",
            "--config",
            workspace["config"],
        ],
    )
    assert start_result.exit_code == 0
    assert "已启动" in start_result.output
    assert "当前步骤: step1" in start_result.output

    advance_result = runner.invoke(
        cli,
        [
            "pipeline",
            "advance",
            "test-pipeline",
            "--config",
            workspace["config"],
        ],
    )
    assert advance_result.exit_code == 0
    assert "已完成" in advance_result.output


def test_pipeline_advance_explicit_run_id_loads_state(workspace, tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    state_dir = tmp_path / "project-state"
    runner = CliRunner()

    start_result = runner.invoke(
        cli,
        [
            "pipeline",
            "start",
            "test-pipeline",
            "--config",
            workspace["config"],
            "--state-dir",
            str(state_dir),
        ],
    )
    assert start_result.exit_code == 0
    run_id = next(
        line.split("Run ID: ", 1)[1].strip()
        for line in start_result.output.splitlines()
        if "Run ID: " in line
    )

    advance_result = runner.invoke(
        cli,
        [
            "pipeline",
            "advance",
            "test-pipeline",
            "--run-id",
            run_id,
            "--config",
            workspace["config"],
            "--state-dir",
            str(state_dir),
        ],
    )

    assert advance_result.exit_code == 0
    assert "已完成" in advance_result.output


def test_pipeline_advance_explicit_run_id_missing_exits_nonzero(workspace, tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    runner = CliRunner()

    result = runner.invoke(
        cli,
        [
            "pipeline",
            "advance",
            "test-pipeline",
            "--run-id",
            "missing-run",
            "--config",
            workspace["config"],
            "--state-dir",
            str(tmp_path / "state"),
        ],
    )

    assert result.exit_code != 0
    assert "找不到运行记录" in result.output


def test_pipeline_state_dir_isolates_latest_runs(workspace, tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    runner = CliRunner()
    state_a = tmp_path / "repo-a" / ".skills-orchestrator"
    state_b = tmp_path / "repo-b" / ".skills-orchestrator"

    start_a = runner.invoke(
        cli,
        [
            "pipeline",
            "start",
            "test-pipeline",
            "--config",
            workspace["config"],
            "--state-dir",
            str(state_a),
        ],
    )
    start_b = runner.invoke(
        cli,
        [
            "pipeline",
            "start",
            "test-pipeline",
            "--config",
            workspace["config"],
            "--state-dir",
            str(state_b),
        ],
    )
    assert start_a.exit_code == 0
    assert start_b.exit_code == 0
    run_a = next(
        line.split("Run ID: ", 1)[1].strip()
        for line in start_a.output.splitlines()
        if "Run ID: " in line
    )
    run_b = next(
        line.split("Run ID: ", 1)[1].strip()
        for line in start_b.output.splitlines()
        if "Run ID: " in line
    )
    assert run_a != run_b

    status_a = runner.invoke(
        cli,
        [
            "pipeline",
            "status",
            "test-pipeline",
            "--config",
            workspace["config"],
            "--state-dir",
            str(state_a),
        ],
    )
    status_b = runner.invoke(
        cli,
        [
            "pipeline",
            "status",
            "test-pipeline",
            "--config",
            workspace["config"],
            "--state-dir",
            str(state_b),
        ],
    )

    assert status_a.exit_code == 0
    assert status_b.exit_code == 0
    assert f"Run: {run_a}" in status_a.output
    assert f"Run: {run_b}" in status_b.output


def test_pipeline_state_dir_env_is_used(workspace, tmp_path, monkeypatch):
    state_dir = tmp_path / "env-state"
    monkeypatch.setenv("SKILLS_ORCHESTRATOR_STATE_DIR", str(state_dir))
    runner = CliRunner()

    result = runner.invoke(
        cli,
        [
            "pipeline",
            "start",
            "test-pipeline",
            "--config",
            workspace["config"],
        ],
    )

    assert result.exit_code == 0
    assert f"State dir: {state_dir}" in result.output
    assert (state_dir / "runs").is_dir()


def test_build_rejects_oversized_forced_skill(workspace, tmp_path):
    skill_path = workspace["root"] / "skills" / "test-skill.md"
    skill_path.write_text(
        skill_path.read_text(encoding="utf-8").replace("load_policy: free", "load_policy: require")
        + "\n"
        + ("A" * 1200),
        encoding="utf-8",
    )

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "build",
            "--config",
            workspace["config"],
            "--output",
            str(tmp_path / "AGENTS.md"),
            "--max-skill-bytes",
            "1000",
        ],
    )

    assert result.exit_code != 0
    assert "exceeds AGENTS.md content limit" in result.output


def test_build_rejects_secret_like_forced_skill_without_echoing_value(workspace, tmp_path):
    skill_path = workspace["root"] / "skills" / "test-skill.md"
    secret_value = "sk-testsecretvalue123456"
    skill_path.write_text(
        skill_path.read_text(encoding="utf-8").replace("load_policy: free", "load_policy: require")
        + f"\napi_key: {secret_value}\n",
        encoding="utf-8",
    )

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "build",
            "--config",
            workspace["config"],
            "--output",
            str(tmp_path / "AGENTS.md"),
        ],
    )

    assert result.exit_code != 0
    assert "secret-like field" in result.output
    assert "api_key" in result.output
    assert secret_value not in result.output
