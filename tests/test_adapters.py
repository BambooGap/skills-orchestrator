import json
import py_compile

from click.testing import CliRunner

from skills_orchestrator.adapters import (
    generate_mcp_client_config,
    generate_openai_agents_sdk_scaffold,
    inspect_adapters,
)
from skills_orchestrator.main import cli


def test_adapter_inspect_detects_claude_skill_entrypoints_only(tmp_path):
    skill_dir = tmp_path / ".claude" / "skills" / "review"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "---\nname: Review\ndescription: Review code\n---\n# Review\n",
        encoding="utf-8",
    )
    (skill_dir / "reference.md").write_text("# Reference\n", encoding="utf-8")

    payload = inspect_adapters(tmp_path)
    claude = next(surface for surface in payload["surfaces"] if surface["id"] == "claude-skills")

    assert claude["detected"] is True
    assert claude["paths"] == [".claude/skills/review/SKILL.md"]
    assert "reference.md" not in json.dumps(claude)
    assert claude["verification"]["status"] == "verified"


def test_adapter_inspect_rejects_malformed_claude_skill_entrypoints(tmp_path):
    skill_dir = tmp_path / ".claude" / "skills" / "broken"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("---\n: bad yaml\n---\n# Broken\n", encoding="utf-8")

    payload = inspect_adapters(tmp_path)
    claude = next(surface for surface in payload["surfaces"] if surface["id"] == "claude-skills")

    assert claude["detected"] is False
    assert claude["paths"] == []
    assert claude["verification"]["invalid_paths"] == [".claude/skills/broken/SKILL.md"]


def test_adapter_inspect_rejects_invalid_mcp_json(tmp_path):
    (tmp_path / ".mcp.json").write_text("{not-json", encoding="utf-8")

    payload = inspect_adapters(tmp_path)
    mcp = next(surface for surface in payload["surfaces"] if surface["id"] == "mcp-client-config")

    assert mcp["detected"] is False
    assert mcp["paths"] == []
    assert mcp["verification"]["invalid_paths"] == [".mcp.json"]


def test_adapter_inspect_detects_openai_agents_sdk_dependency(tmp_path):
    (tmp_path / "pyproject.toml").write_text(
        '[project]\ndependencies = ["openai-agents>=0.4"]\n',
        encoding="utf-8",
    )

    payload = inspect_adapters(tmp_path)
    openai = next(
        surface for surface in payload["surfaces"] if surface["id"] == "openai-agents-sdk"
    )

    assert openai["detected"] is True
    assert openai["paths"] == ["pyproject.toml"]


def test_mcp_client_config_scaffold_uses_absolute_config(tmp_path):
    config = tmp_path / "config" / "skills.yaml"
    config.parent.mkdir()
    config.write_text("zones: []\n", encoding="utf-8")

    payload = generate_mcp_client_config(str(config), zone="enterprise")
    args = payload["mcpServers"]["skills-orchestrator"]["args"]

    assert args[:2] == ["serve", "--config"]
    assert args[2] == str(config.resolve())
    assert args[-2:] == ["--zone", "enterprise"]


def test_openai_agents_sdk_scaffold_compiles(tmp_path):
    config = tmp_path / "config" / "skills.yaml"
    config.parent.mkdir()
    config.write_text("zones: []\n", encoding="utf-8")
    scaffold = tmp_path / "openai_skillops_agent.py"
    scaffold.write_text(generate_openai_agents_sdk_scaffold(str(config)), encoding="utf-8")

    py_compile.compile(str(scaffold), doraise=True)
    content = scaffold.read_text(encoding="utf-8")
    assert "MCPServerStdio" in content
    assert "mcp_servers=[server]" in content


def test_adapters_cli_json_and_export(tmp_path):
    config = tmp_path / "config" / "skills.yaml"
    config.parent.mkdir()
    config.write_text("zones: []\n", encoding="utf-8")
    runner = CliRunner()

    inspect_result = runner.invoke(
        cli, ["adapters", "inspect", "--path", str(tmp_path), "--format", "json"]
    )
    export_result = runner.invoke(
        cli,
        [
            "adapters",
            "export",
            "mcp-client-config",
            "--config",
            str(config),
        ],
    )

    assert inspect_result.exit_code == 0
    assert json.loads(inspect_result.output)["schema_version"] == "skills-orchestrator.adapters.v1"
    assert export_result.exit_code == 0
    assert json.loads(export_result.output)["mcpServers"]["skills-orchestrator"]["command"]
