import yaml
from click.testing import CliRunner

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
