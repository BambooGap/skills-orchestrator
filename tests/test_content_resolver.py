"""SkillContentResolver 测试 — 统一内容读取入口"""

import tempfile
from pathlib import Path

from skills_orchestrator.compiler.content_resolver import SkillContentResolver
from skills_orchestrator.models import SkillMeta


def _make_skill_file(tmpdir, skill_id: str, content: str) -> str:
    """创建临时 skill 文件，返回路径"""
    tmpdir = Path(tmpdir)
    path = tmpdir / f"{skill_id}.md"
    path.write_text(content, encoding="utf-8")
    return str(path)


class TestSkillContentResolverDirectRead:
    """无 registry 时的直接文件读取"""

    def test_read_simple_skill(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            path = _make_skill_file(tmpdir, "tdd", "---\nid: tdd\n---\n# TDD Content")

            skill = SkillMeta(id="tdd", name="TDD", path=path, summary="TDD")
            resolver = SkillContentResolver(base_dir=str(tmpdir))
            content = resolver.read(skill)
            assert "# TDD Content" in content

    def test_read_missing_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            skill = SkillMeta(
                id="missing", name="Missing", path="/nonexistent.md", summary="Missing"
            )
            resolver = SkillContentResolver(base_dir=str(tmpdir))
            content = resolver.read(skill)
            assert "文件不存在" in content

    def test_read_with_base_inheritance(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            base_path = _make_skill_file(
                tmpdir, "base-skill", "---\nid: base-skill\n---\n# Base Content\n\nBase rules here."
            )
            child_path = _make_skill_file(
                tmpdir,
                "child-skill",
                "---\nid: child-skill\nbase: base-skill\n---\n# Child Addition",
            )

            base_skill = SkillMeta(id="base-skill", name="Base", path=base_path, summary="Base")
            child_skill = SkillMeta(
                id="child-skill", name="Child", path=child_path, summary="Child", base="base-skill"
            )

            # 传入 skills 列表，让 resolver 能找到 base skill
            resolver = SkillContentResolver(base_dir=str(tmpdir), skills=[base_skill, child_skill])

            # 先读 base，缓存它
            base_content = resolver.read(base_skill)
            assert "Base Content" in base_content

            # 读 child，应合并 base
            child_content = resolver.read(child_skill)
            assert "Base Content" in child_content
            assert "Child Addition" in child_content

    def test_read_caches_result(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            path = _make_skill_file(tmpdir, "cached", "---\nid: cached\n---\n# Original")

            skill = SkillMeta(id="cached", name="Cached", path=path, summary="Cached")
            resolver = SkillContentResolver(base_dir=str(tmpdir))

            content1 = resolver.read(skill)
            # 修改文件
            Path(path).write_text("---\nid: cached\n---\n# Modified", encoding="utf-8")
            content2 = resolver.read(skill)
            # 应返回缓存的内容
            assert content1 == content2
            assert "Original" in content2

    def test_read_relative_path(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            skill_dir = tmpdir / "skills"
            skill_dir.mkdir()
            skill_file = skill_dir / "my-skill.md"
            skill_file.write_text("---\nid: my-skill\n---\n# My Skill", encoding="utf-8")

            skill = SkillMeta(
                id="my-skill", name="My Skill", path="skills/my-skill.md", summary="My"
            )
            resolver = SkillContentResolver(base_dir=str(tmpdir))
            content = resolver.read(skill)
            assert "# My Skill" in content

    def test_base_inheritance_without_skills_list_graceful(self):
        """无 registry 也无 skills 列表时，base 继承降级为返回原始内容（不崩溃）"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            child_path = _make_skill_file(
                tmpdir, "orphan", "---\nid: orphan\nbase: unknown-base\n---\n# Orphan"
            )

            skill = SkillMeta(
                id="orphan", name="Orphan", path=child_path, summary="Orphan", base="unknown-base"
            )
            resolver = SkillContentResolver(base_dir=str(tmpdir))
            content = resolver.read(skill)
            # 应返回原始内容（不合并 base，因为找不到 base skill）
            assert "# Orphan" in content


class TestSkillContentResolverWithRegistry:
    """有 registry 时的内容读取（代理到 registry.get_content）"""

    def test_delegates_to_registry(self):
        """当传入 registry 时，优先走 registry.get_content()"""
        from unittest.mock import MagicMock

        registry = MagicMock()
        registry.get_content.return_value = "---\nid: tdd\n---\n# From Registry"

        skill = SkillMeta(id="tdd", name="TDD", path="/fake/path.md", summary="TDD")
        resolver = SkillContentResolver(base_dir="/tmp", registry=registry)
        content = resolver.read(skill)

        assert "From Registry" in content
        registry.get_content.assert_called_once_with("tdd")

    def test_fallback_on_registry_failure(self):
        """registry 抛异常时降级为文件直读"""
        from unittest.mock import MagicMock

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            path = _make_skill_file(tmpdir, "tdd", "---\nid: tdd\n---\n# From File")

            registry = MagicMock()
            registry.get_content.side_effect = RuntimeError("registry broken")

            skill = SkillMeta(id="tdd", name="TDD", path=path, summary="TDD")
            resolver = SkillContentResolver(base_dir=str(tmpdir), registry=registry)
            content = resolver.read(skill)

            assert "From File" in content

    def test_fallback_on_registry_returns_none(self):
        """registry 返回 None 时降级为文件直读"""
        from unittest.mock import MagicMock

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            path = _make_skill_file(tmpdir, "tdd", "---\nid: tdd\n---\n# From File")

            registry = MagicMock()
            registry.get_content.return_value = None

            skill = SkillMeta(id="tdd", name="TDD", path=path, summary="TDD")
            resolver = SkillContentResolver(base_dir=str(tmpdir), registry=registry)
            content = resolver.read(skill)

            assert "From File" in content
