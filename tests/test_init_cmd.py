import yaml
from click.testing import CliRunner

from skills_orchestrator.checker import run_check
from skills_orchestrator.cli.init_cmd import init


def test_init_non_interactive_happy_path(tmp_path):
    runner = CliRunner()

    # Setup
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    skill_file = skills_dir / "test-skill.md"
    skill_file.write_text(
        """---
id: test-id
name: Test Name
summary: Test Summary
tags: [test, mock]
load_policy: require
priority: 99
zones: [test-zone]
conflict_with: [other]
---
# Test Content
""",
        encoding="utf-8",
    )

    output_yaml = tmp_path / "skills.yaml"

    result = runner.invoke(
        init,
        [
            "--skills-dir",
            str(skills_dir),
            "--output",
            str(output_yaml),
            "--non-interactive",
        ],
    )

    assert result.exit_code == 0
    assert "找到 1 个 skill 文件" in result.output
    assert output_yaml.exists()

    with open(output_yaml, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    assert len(config["skills"]) == 1
    skill = config["skills"][0]
    assert skill["id"] == "test-id"
    assert skill["name"] == "Test Name"
    assert skill["summary"] == "Test Summary"
    assert skill["tags"] == ["test", "mock"]
    assert skill["load_policy"] == "require"
    assert skill["priority"] == 99
    assert skill["zones"] == ["test-zone"]
    assert skill["path"] == "${SKILLS_ROOT}/test-skill.md"


def test_init_skills_dir_not_exists(tmp_path):
    runner = CliRunner()
    skills_dir = tmp_path / "missing_skills"
    output_yaml = tmp_path / "skills.yaml"

    result = runner.invoke(
        init,
        [
            "--skills-dir",
            str(skills_dir),
            "--output",
            str(output_yaml),
            "--non-interactive",
        ],
    )

    assert result.exit_code == 0
    assert "已创建目录" in result.output
    assert skills_dir.exists()
    assert "没有 .md 文件" in result.output
    assert not output_yaml.exists()


def test_init_no_md_files(tmp_path):
    runner = CliRunner()
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    output_yaml = tmp_path / "skills.yaml"

    result = runner.invoke(
        init,
        [
            "--skills-dir",
            str(skills_dir),
            "--output",
            str(output_yaml),
            "--non-interactive",
        ],
    )

    assert result.exit_code == 0
    assert "没有 .md 文件" in result.output
    assert not output_yaml.exists()


def test_init_interactive_mode(tmp_path):
    runner = CliRunner()
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    skill_file = skills_dir / "my-skill.md"
    skill_file.write_text("# Just some content", encoding="utf-8")
    output_yaml = tmp_path / "skills.yaml"

    # Simulate user input
    user_inputs = [
        "Custom Name",  # 名称
        "Custom Summary",  # 简介
        "tag1, tag2",  # 标签
        "require",  # 加载策略
        "88",  # 优先级
    ]

    result = runner.invoke(
        init,
        ["--skills-dir", str(skills_dir), "--output", str(output_yaml)],
        input="\n".join(user_inputs) + "\n",
    )

    assert result.exit_code == 0
    assert output_yaml.exists()

    with open(output_yaml, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    skill = config["skills"][0]
    assert skill["id"] == "my-skill"
    assert skill["name"] == "Custom Name"
    assert skill["summary"] == "Custom Summary"
    assert skill["tags"] == ["tag1", "tag2"]
    assert skill["load_policy"] == "require"
    assert skill["priority"] == 88


def test_init_missing_frontmatter_non_interactive(tmp_path):
    runner = CliRunner()
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    skill_file = skills_dir / "my-new-skill.md"
    skill_file.write_text("Just some random content without H1", encoding="utf-8")
    output_yaml = tmp_path / "skills.yaml"

    result = runner.invoke(
        init,
        [
            "--skills-dir",
            str(skills_dir),
            "--output",
            str(output_yaml),
            "--non-interactive",
        ],
    )

    assert result.exit_code == 0
    assert "缺少 frontmatter，使用了推断默认值" in result.output
    assert output_yaml.exists()

    with open(output_yaml, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    skill = config["skills"][0]
    assert skill["id"] == "my-new-skill"
    assert skill["name"] == "My New Skill"
    assert skill["load_policy"] == "free"
    assert skill["priority"] == 50


def test_init_team_standard_template_generates_portable_scaffold(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()

    result = runner.invoke(init, ["--template", "team-standard"])

    assert result.exit_code == 0
    config_path = tmp_path / "config" / "skills.yaml"
    assert config_path.exists()
    assert (tmp_path / "skills" / "team" / "engineering-standards.md").exists()
    assert (tmp_path / "skills" / "team" / "code-review.md").exists()
    assert (tmp_path / "skills" / "team" / "release-checklist.md").exists()
    assert (tmp_path / "config" / "pipelines" / "team-review.yaml").exists()
    assert (tmp_path / ".github" / "workflows" / "skills-orchestrator.yml").exists()
    assert (tmp_path / "evidence" / ".gitkeep").exists()
    assert not (tmp_path / "AGENTS.md").exists()
    assert "skills-orchestrator build --config" in result.output
    assert "doctor --config" in result.output
    assert "build --lock before expecting doctor 100/100" in result.output

    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    assert config["skill_dirs"] == ["../skills"]
    assert "SKILLS_ROOT" not in config_path.read_text(encoding="utf-8")
    workflow = (tmp_path / ".github" / "workflows" / "skills-orchestrator.yml").read_text(
        encoding="utf-8"
    )
    assert "security-events: write" not in workflow
    assert "upload-sarif: true" not in workflow

    report = run_check(str(config_path), policy_packs=["builtin/team-standard"])
    assert report.diagnostics == []


def test_init_team_standard_hardened_workflow_pins_checkout(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()

    result = runner.invoke(init, ["--template", "team-standard", "--hardened-workflow"])

    assert result.exit_code == 0
    workflow = (tmp_path / ".github" / "workflows" / "skills-orchestrator.yml").read_text(
        encoding="utf-8"
    )
    assert "--hardened-workflow" in workflow
    assert "actions/checkout@9c091bb21b7c1c1d1991bb908d89e4e9dddfe3e0" in workflow
    assert "actions/checkout@v4" not in workflow
    assert "BambooGap/skills-orchestrator@" in workflow


def test_init_team_standard_custom_output_writes_relative_skill_dirs(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()

    result = runner.invoke(init, ["--template", "team-standard", "--output", "skills.yaml"])

    assert result.exit_code == 0
    config = yaml.safe_load((tmp_path / "skills.yaml").read_text(encoding="utf-8"))
    assert config["skill_dirs"] == ["skills"]


def test_init_team_standard_existing_file_requires_force(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    existing = config_dir / "skills.yaml"
    existing.write_text("existing: true\n", encoding="utf-8")
    runner = CliRunner()

    result = runner.invoke(init, ["--template", "team-standard"])

    assert result.exit_code == 1
    assert "目标文件已存在" in result.output
    assert not (tmp_path / "skills").exists()

    force_result = runner.invoke(init, ["--template", "team-standard", "--force"])

    assert force_result.exit_code == 0
    assert "skill_dirs" in existing.read_text(encoding="utf-8")


def test_init_team_standard_rejects_output_path_escape(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()

    result = runner.invoke(init, ["--template", "team-standard", "--output", "../outside.yaml"])

    assert result.exit_code == 1
    assert "--output 不允许包含 '..'" in result.output
    assert not (tmp_path / "skills").exists()
