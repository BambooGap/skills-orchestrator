import json
import py_compile
import shutil
from pathlib import Path

from click.testing import CliRunner

from skills_orchestrator.adapters import (
    export_claude_skill_bundles,
    generate_mcp_client_config,
    generate_openai_agents_sdk_scaffold,
    inspect_adapters,
)
from skills_orchestrator.compiler import Parser
from skills_orchestrator.main import cli


ROOT = Path(__file__).resolve().parents[1]


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


def test_claude_skills_export_round_trips_skillops_metadata(tmp_path):
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    (skills_dir / "release.md").write_text(
        "---\n"
        "id: release-check\n"
        "name: Release Check\n"
        "summary: Review release evidence\n"
        "tags: [release, evidence]\n"
        "load_policy: require\n"
        "priority: 90\n"
        "zones: [default]\n"
        "owner: release-team\n"
        "source: repo://skills/release.md\n"
        "version: 1.2.3\n"
        "lifecycle: active\n"
        "approvers: [release-team]\n"
        "reviewed_at: 2026-06-20\n"
        "expires_at: 2026-12-20\n"
        "license: MIT\n"
        "provenance:\n"
        "  source_url: https://github.com/example/skills/blob/main/release.md\n"
        "  source_commit: abc123\n"
        "  content_hash: sha256:abc\n"
        "---\n"
        "# Release Check\n\nCheck release evidence.\n",
        encoding="utf-8",
    )
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    config = config_dir / "skills.yaml"
    config.write_text(
        "skill_dirs:\n"
        "  - ../skills\n"
        "zones:\n"
        "  - id: default\n"
        "    name: Default\n"
        "    load_policy: free\n"
        "    rules: []\n",
        encoding="utf-8",
    )

    manifest = export_claude_skill_bundles(str(config), tmp_path / ".claude" / "skills")
    exported_config = tmp_path / "exported.yaml"
    exported_config.write_text(
        "skill_dirs:\n"
        "  - .claude/skills\n"
        "zones:\n"
        "  - id: default\n"
        "    name: Default\n"
        "    load_policy: free\n"
        "    rules: []\n",
        encoding="utf-8",
    )
    exported = Parser(str(exported_config)).parse().skills[0]

    assert manifest["summary"]["exported"] == 1
    assert exported.id == "release-check"
    assert exported.owner == "release-team"
    assert exported.source == "repo://skills/release.md"
    assert exported.version == "1.2.3"
    assert exported.license == "MIT"
    assert exported.provenance["source_commit"] == "abc123"


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


def test_adapters_cli_exports_claude_skills(tmp_path):
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    (skills_dir / "review.md").write_text(
        "---\nid: review\nname: Review\nsummary: Review code\nowner: platform\n---\n# Review\n",
        encoding="utf-8",
    )
    config = tmp_path / "config" / "skills.yaml"
    config.parent.mkdir()
    config.write_text(
        "skill_dirs:\n"
        "  - ../skills\n"
        "zones:\n"
        "  - id: default\n"
        "    name: Default\n"
        "    load_policy: free\n"
        "    rules: []\n",
        encoding="utf-8",
    )
    manifest = tmp_path / "claude-export.json"
    runner = CliRunner()

    result = runner.invoke(
        cli,
        [
            "adapters",
            "export",
            "claude-skills",
            "--config",
            str(config),
            "--output-dir",
            str(tmp_path / ".claude" / "skills"),
            "--manifest-output",
            str(manifest),
        ],
    )

    assert result.exit_code == 0
    assert (tmp_path / ".claude" / "skills" / "review" / "SKILL.md").exists()
    assert json.loads(manifest.read_text(encoding="utf-8"))["summary"]["exported"] == 1


def test_adapter_evidence_example_generates_all_surfaces(tmp_path):
    example = tmp_path / "adapter-evidence"
    shutil.copytree(ROOT / "examples" / "adapter-evidence", example)
    evidence = example / "evidence"
    evidence.mkdir()
    config = example / "config" / "skills.yaml"
    runner = CliRunner()

    check_result = runner.invoke(
        cli,
        [
            "check",
            "--config",
            str(config),
            "--policy-pack",
            "builtin/engineering-grade",
            "--fail-on",
            "warning",
        ],
    )
    build_result = runner.invoke(
        cli,
        [
            "build",
            "--config",
            str(config),
            "--output",
            str(example / "AGENTS.md"),
        ],
    )
    claude_result = runner.invoke(
        cli,
        [
            "adapters",
            "export",
            "claude-skills",
            "--config",
            str(config),
            "--output-dir",
            str(example / ".claude" / "skills"),
            "--manifest-output",
            str(evidence / "claude-skills-export.json"),
            "--force",
        ],
    )
    mcp_result = runner.invoke(
        cli,
        [
            "adapters",
            "export",
            "mcp-client-config",
            "--config",
            str(config),
            "--output",
            str(example / ".mcp.json"),
            "--force",
        ],
    )
    openai_result = runner.invoke(
        cli,
        [
            "adapters",
            "export",
            "openai-agents-sdk",
            "--config",
            str(config),
            "--output",
            str(evidence / "openai_skillops_agent.py"),
            "--force",
        ],
    )
    inspect_result = runner.invoke(
        cli, ["adapters", "inspect", "--path", str(example), "--format", "json"]
    )

    assert check_result.exit_code == 0, check_result.output
    assert build_result.exit_code == 0, build_result.output
    assert claude_result.exit_code == 0, claude_result.output
    assert mcp_result.exit_code == 0, mcp_result.output
    assert openai_result.exit_code == 0, openai_result.output
    py_compile.compile(str(evidence / "openai_skillops_agent.py"), doraise=True)
    assert inspect_result.exit_code == 0, inspect_result.output

    manifest = json.loads((evidence / "claude-skills-export.json").read_text(encoding="utf-8"))
    assert manifest["summary"]["exported"] == 2
    exported_skill = example / ".claude" / "skills" / "release-trust" / "SKILL.md"
    assert "owner: release-team" in exported_skill.read_text(encoding="utf-8")

    inspect_payload = json.loads(inspect_result.output)
    detected = {surface["id"] for surface in inspect_payload["surfaces"] if surface["detected"]}
    assert {
        "agents-md",
        "claude-skills",
        "mcp-client-config",
        "openai-agents-sdk",
    } <= detected
