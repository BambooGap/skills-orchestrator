"""MCP CLI (mcp-test command) tests.

Validates two layers:
1. ToolExecutor: raises ValueError for nonexistent get_skill (doesn't swallow exceptions)
2. CLI: mcp-test get_skill nonexistent returns non-zero exit code with clear error
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from skills_orchestrator.main import cli
from skills_orchestrator.models import SkillMeta
from skills_orchestrator.mcp.tools import ToolExecutor


# ── Fixtures ──────────────────────────────────────────────────────


def _mock_registry():
    """Return a mock SkillRegistry with minimal skills."""
    reg = MagicMock()

    skill = SkillMeta(
        id="test-skill",
        name="Test Skill",
        path="/fake/test-skill.md",
        summary="A test skill",
        tags=["test"],
        load_policy="free",
        priority=50,
        zones=["default"],
        conflict_with=[],
    )
    reg.all.return_value = [skill]
    reg.get_meta.return_value = skill
    reg.get_content.side_effect = lambda sid: (
        "# Test Skill\nContent" if sid == "test-skill" else None
    )
    reg.combos.return_value = []
    return reg


# ═══════════════════════════════════════════════════════════════════
# ToolExecutor layer: executor doesn't swallow exceptions
# ═══════════════════════════════════════════════════════════════════


class TestToolExecutorNoSwallow:
    """Verify ToolExecutor raises ValueError for nonexistent skill id."""

    def test_get_skill_nonexistent_raises(self):
        """_get_skill must raise ValueError for nonexistent id — not return empty or None."""
        executor = ToolExecutor(_mock_registry())
        with pytest.raises(ValueError, match="找不到"):
            executor.execute("get_skill", {"id": "nonexistent-skill"})

    def test_get_skill_nonexistent_suggests_similar(self):
        """Error message should include similar skill ids when available."""
        executor = ToolExecutor(_mock_registry())
        with pytest.raises(ValueError, match="test-skill"):
            executor.execute("get_skill", {"id": "test"})

    def test_get_skill_existing_works(self):
        """Existing skill returns content without error."""
        executor = ToolExecutor(_mock_registry())
        results = executor.execute("get_skill", {"id": "test-skill"})
        text = "\n".join(r.text for r in results)
        assert "Test Skill" in text

    def test_list_skills_works(self):
        """list_skills should work without error."""
        executor = ToolExecutor(_mock_registry())
        results = executor.execute("list_skills", {})
        text = "\n".join(r.text for r in results)
        assert "test-skill" in text

    def test_unknown_tool_returns_message(self):
        """Unknown tool name returns a message, not an exception."""
        executor = ToolExecutor(_mock_registry())
        results = executor.execute("unknown_tool", {})
        text = "\n".join(r.text for r in results)
        assert "未知工具" in text


# ═══════════════════════════════════════════════════════════════════
# CLI layer: mcp-test returns non-zero for errors
# ═══════════════════════════════════════════════════════════════════


class TestMcpTestCLI:
    """Test the mcp-test CLI command's error handling behavior.

    We patch SkillRegistry at the point of use inside mcp_test()
    to inject a registry that returns None for nonexistent skills.
    """

    @patch("skills_orchestrator.mcp.registry.SkillRegistry")
    def test_nonexistent_skill_returns_nonzero(self, MockRegistry, tmp_path):
        """mcp-test get_skill nonexistent must return non-zero exit code."""
        # Create a minimal config file so SkillRegistry init doesn't fail
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        (config_dir / "skills.yaml").write_text('version: "1.0"\nzones: []\nskill_dirs: []\n')

        # Setup mock: get_content returns None for nonexistent, content for existing
        mock_instance = MagicMock()
        mock_instance.all.return_value = []
        mock_instance.get_content.return_value = None
        mock_instance.get_meta.return_value = None
        mock_instance.combos.return_value = []
        MockRegistry.return_value = mock_instance

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "mcp-test",
                "get_skill",
                '{"id": "nonexistent-skill"}',
                "-c",
                str(config_dir / "skills.yaml"),
            ],
        )
        assert result.exit_code != 0, (
            f"Expected non-zero exit code for nonexistent skill, got {result.exit_code}.\n"
            f"output: {result.output}"
        )

    @patch("skills_orchestrator.mcp.registry.SkillRegistry")
    def test_nonexistent_skill_shows_error(self, MockRegistry, tmp_path):
        """mcp-test get_skill nonexistent must show clear error message."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        (config_dir / "skills.yaml").write_text('version: "1.0"\nzones: []\nskill_dirs: []\n')

        mock_instance = MagicMock()
        mock_instance.all.return_value = []
        mock_instance.get_content.return_value = None
        mock_instance.get_meta.return_value = None
        mock_instance.combos.return_value = []
        MockRegistry.return_value = mock_instance

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "mcp-test",
                "get_skill",
                '{"id": "nonexistent-skill"}',
                "-c",
                str(config_dir / "skills.yaml"),
            ],
        )
        assert "找不到" in result.output or "nonexistent" in result.output, (
            f"Expected clear error about missing skill.\noutput: {result.output}"
        )

    def test_invalid_json_returns_nonzero(self, tmp_path):
        """mcp-test with invalid JSON args must return non-zero exit code."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        (config_dir / "skills.yaml").write_text('version: "1.0"\nzones: []\nskill_dirs: []\n')

        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["mcp-test", "get_skill", "not-valid-json", "-c", str(config_dir / "skills.yaml")],
        )
        assert result.exit_code != 0
        assert "JSON" in result.output or "解析" in result.output
