"""Sync 模块测试 — SyncTarget 实现和 SyncEngine"""

import os
from pathlib import Path

import pytest
import yaml

from skills_orchestrator.models import ResolvedConfig, SkillMeta
from skills_orchestrator.sync.targets import (
    SyncTarget,
    HermesTarget,
    OpenClawTarget,
    CopilotTarget,
    AgentsMdTarget,
    CursorTarget,
    SyncEngine,
    get_target,
    TARGET_REGISTRY,
)


# ── helpers ──────────────────────────────────────────────────────


def _make_skill(id, name, summary, tags, path=None, load_policy="free", priority=50):
    return SkillMeta(
        id=id,
        name=name,
        path=path or f"/fake/{id}.md",
        summary=summary,
        tags=tags,
        load_policy=load_policy,
        priority=priority,
        zones=["default"],
        conflict_with=[],
    )


def _make_resolved(forced=None, passive=None, blocked=None, base_dir="/tmp"):
    return ResolvedConfig(
        forced_skills=forced or [],
        passive_skills=passive or [],
        blocked_skills=blocked or [],
        base_dir=base_dir,
    )


SAMPLE_SKILL_CONTENT = """---
id: tdd
name: 测试驱动开发
summary: 先写测试再写实现
tags: [testing, tdd]
load_policy: require
priority: 80
---

# 测试驱动开发

1. 写一个失败的测试
2. 写最少代码让测试通过
3. 重构
"""

SAMPLE_SKILL_NO_FM = """# 代码风格规范

使用一致的命名约定。
"""


# ── TARGET_REGISTRY 测试 ────────────────────────────────────────


class TestTargetRegistry:
    def test_all_targets_registered(self):
        assert "hermes" in TARGET_REGISTRY
        assert "openclaw" in TARGET_REGISTRY
        assert "copilot" in TARGET_REGISTRY
        assert "agents-md" in TARGET_REGISTRY

    def test_get_target_hermes(self):
        t = get_target("hermes")
        assert isinstance(t, HermesTarget)

    def test_get_target_openclaw(self):
        t = get_target("openclaw")
        assert isinstance(t, OpenClawTarget)

    def test_get_target_copilot(self):
        t = get_target("copilot")
        assert isinstance(t, CopilotTarget)

    def test_get_target_agents_md(self):
        t = get_target("agents-md")
        assert isinstance(t, AgentsMdTarget)

    def test_get_target_unknown_raises(self):
        with pytest.raises(ValueError, match="未知的同步目标"):
            get_target("nonexistent")

    def test_get_target_with_kwargs(self):
        t = get_target("hermes", base_dir="/tmp/test-hermes")
        assert t.base_dir == Path("/tmp/test-hermes")


# ── HermesTarget 测试 ────────────────────────────────────────────


class TestHermesTarget:
    def test_write_skill_with_frontmatter(self, tmp_path):
        target = HermesTarget(base_dir=str(tmp_path / "skills"))
        target.prepare()
        meta = {"name": "TDD", "summary": "测试驱动开发", "tags": ["testing", "tdd"]}
        target.write("tdd", SAMPLE_SKILL_CONTENT, meta)
        count = target.finalize()
        assert count == 1

        skill_file = tmp_path / "skills" / "software-development" / "tdd" / "SKILL.md"
        assert skill_file.exists()
        content = skill_file.read_text()
        assert "测试驱动开发" in content
        assert content.startswith("---")

    def test_write_skill_without_frontmatter(self, tmp_path):
        target = HermesTarget(base_dir=str(tmp_path / "skills"))
        target.prepare()
        meta = {"name": "代码风格", "summary": "命名约定", "tags": ["style"]}
        target.write("code-style", SAMPLE_SKILL_NO_FM, meta)
        count = target.finalize()
        assert count == 1

        skill_file = tmp_path / "skills" / "software-development" / "code-style" / "SKILL.md"
        assert skill_file.exists()
        content = skill_file.read_text()
        # 补了 frontmatter
        assert content.startswith("---")
        assert "代码风格规范" in content

    def test_category_inference_from_tags(self, tmp_path):
        target = HermesTarget(base_dir=str(tmp_path / "skills"))
        target.prepare()

        # coding tag → software-development
        meta_code = {"name": "A", "summary": "s", "tags": ["coding"]}
        target.write("a", "# A", meta_code)

        # deployment tag → devops
        meta_ops = {"name": "B", "summary": "s", "tags": ["deployment"]}
        target.write("b", "# B", meta_ops)

        # planning tag → productivity
        meta_plan = {"name": "C", "summary": "s", "tags": ["planning"]}
        target.write("c", "# C", meta_plan)

        # no known tag → general
        meta_misc = {"name": "D", "summary": "s", "tags": ["unknown"]}
        target.write("d", "# D", meta_misc)

        target.finalize()

        assert (tmp_path / "skills" / "software-development" / "a" / "SKILL.md").exists()
        assert (tmp_path / "skills" / "devops" / "b" / "SKILL.md").exists()
        assert (tmp_path / "skills" / "productivity" / "c" / "SKILL.md").exists()
        assert (tmp_path / "skills" / "general" / "d" / "SKILL.md").exists()

    def test_category_override(self, tmp_path):
        target = HermesTarget(base_dir=str(tmp_path / "skills"), category_override="custom")
        target.prepare()
        meta = {"name": "A", "summary": "s", "tags": ["coding"]}
        target.write("a", "# A", meta)
        target.finalize()
        assert (tmp_path / "skills" / "custom" / "a" / "SKILL.md").exists()

    def test_default_base_dir(self):
        target = HermesTarget()
        assert target.base_dir == Path(os.path.expanduser("~/.hermes/skills"))

    def test_rejects_path_traversal_skill_id(self, tmp_path):
        target = HermesTarget(base_dir=str(tmp_path / "skills"))
        target.prepare()
        with pytest.raises(ValueError, match="非法 skill_id"):
            target.write("../../../etc/pwned", "# Evil", {"name": "Evil", "summary": "s"})
        assert not (tmp_path / "etc").exists()

    def test_allows_chinese_skill_id(self, tmp_path):
        target = HermesTarget(base_dir=str(tmp_path / "skills"))
        target.prepare()
        target.write("安全重构", "# 安全重构", {"name": "安全重构", "summary": "s"})
        target.finalize()
        assert (tmp_path / "skills" / "general" / "安全重构" / "SKILL.md").exists()


# ── OpenClawTarget 测试 ──────────────────────────────────────────


class TestOpenClawTarget:
    def test_write_skill_with_frontmatter(self, tmp_path):
        target = OpenClawTarget(base_dir=str(tmp_path / "skills"))
        target.prepare()
        meta = {"name": "TDD", "summary": "测试驱动开发", "tags": ["testing"]}
        target.write("tdd", SAMPLE_SKILL_CONTENT, meta)
        count = target.finalize()
        assert count == 1

        skill_file = tmp_path / "skills" / "tdd" / "SKILL.md"
        assert skill_file.exists()
        content = skill_file.read_text()
        assert content.startswith("---")
        # 解析 frontmatter 确认有 name 和 description
        fm_end = content.find("\n---", 3)
        fm = yaml.safe_load(content[3:fm_end])
        assert fm.get("name")
        assert fm.get("description")

    def test_auto_patch_description_from_summary(self, tmp_path):
        """如果 frontmatter 有 summary 没有 description，自动补 description"""
        target = OpenClawTarget(base_dir=str(tmp_path / "skills"))
        target.prepare()

        content_no_desc = """---
name: My Skill
summary: 这是个摘要
---

# 内容
"""
        meta = {"name": "My Skill", "summary": "这是个摘要"}
        target.write("my-skill", content_no_desc, meta)
        target.finalize()

        skill_file = tmp_path / "skills" / "my-skill" / "SKILL.md"
        content = skill_file.read_text()
        fm_end = content.find("\n---", 3)
        fm = yaml.safe_load(content[3:fm_end])
        assert fm.get("description") == "这是个摘要"

    def test_write_skill_without_frontmatter(self, tmp_path):
        target = OpenClawTarget(base_dir=str(tmp_path / "skills"))
        target.prepare()
        meta = {"name": "风格", "summary": "代码风格", "tags": ["style"]}
        target.write("code-style", SAMPLE_SKILL_NO_FM, meta)
        target.finalize()

        skill_file = tmp_path / "skills" / "code-style" / "SKILL.md"
        assert skill_file.exists()
        content = skill_file.read_text()
        assert content.startswith("---")
        fm_end = content.find("\n---", 3)
        fm = yaml.safe_load(content[3:fm_end])
        assert fm["name"] == "风格"
        assert fm["description"] == "代码风格"

    def test_no_category_subdir(self, tmp_path):
        """OpenClaw 不像 Hermes 有 category 层，直接 skill_id/SKILL.md"""
        target = OpenClawTarget(base_dir=str(tmp_path / "skills"))
        target.prepare()
        meta = {"name": "A", "summary": "s"}
        target.write("my-skill", "# A", meta)
        target.finalize()
        assert (tmp_path / "skills" / "my-skill" / "SKILL.md").exists()
        # 不应该有 category 层
        assert not (tmp_path / "skills" / "general").exists()

    def test_default_base_dir(self):
        target = OpenClawTarget()
        assert target.base_dir == Path(os.path.expanduser("~/.openclaw/workspace/skills"))

    def test_rejects_path_traversal_skill_id(self, tmp_path):
        target = OpenClawTarget(base_dir=str(tmp_path / "skills"))
        target.prepare()
        with pytest.raises(ValueError, match="非法 skill_id"):
            target.write("../../../etc/pwned", "# Evil", {"name": "Evil", "summary": "s"})
        assert not (tmp_path / "etc").exists()

    def test_allows_chinese_skill_id(self, tmp_path):
        target = OpenClawTarget(base_dir=str(tmp_path / "skills"))
        target.prepare()
        target.write("安全重构", "# 安全重构", {"name": "安全重构", "summary": "s"})
        target.finalize()
        assert (tmp_path / "skills" / "安全重构" / "SKILL.md").exists()


class TestCursorTarget:
    def test_rejects_path_traversal_skill_id(self, tmp_path):
        target = CursorTarget(output_dir=str(tmp_path))
        target.prepare()
        with pytest.raises(ValueError, match="非法 skill_id"):
            target.write("../../../etc/pwned", "# Evil", {"name": "Evil", "summary": "s"})
        assert not (tmp_path / "etc").exists()

    def test_allows_chinese_skill_id(self, tmp_path):
        target = CursorTarget(output_dir=str(tmp_path))
        target.prepare()
        target.write("安全重构", "# 安全重构", {"name": "安全重构", "summary": "s"})
        target.finalize()
        assert (tmp_path / ".cursor" / "rules" / "安全重构.mdc").exists()


# ── CopilotTarget 测试 ───────────────────────────────────────────


class TestCopilotTarget:
    def test_write_and_finalize(self, tmp_path):
        out = tmp_path / ".github" / "copilot-instructions.md"
        target = CopilotTarget(output_path=str(out))
        target.prepare()

        meta = {"name": "TDD", "summary": "测试驱动"}
        target.write("tdd", SAMPLE_SKILL_CONTENT, meta)
        count = target.finalize()
        assert count == 1
        assert out.exists()
        content = out.read_text()
        assert "Generated by Skills Orchestrator" in content
        assert "测试驱动开发" in content

    def test_prepare_creates_github_dir(self, tmp_path):
        out = tmp_path / "sub" / ".github" / "copilot-instructions.md"
        target = CopilotTarget(output_path=str(out))
        target.prepare()
        assert out.parent.exists()

    def test_aggregation_multiple_skills(self, tmp_path):
        out = tmp_path / "copilot-instructions.md"
        target = CopilotTarget(output_path=str(out))
        target.prepare()

        meta1 = {"name": "A", "summary": "s1"}
        meta2 = {"name": "B", "summary": "s2"}
        target.write("skill-a", "# Skill A\n\nContent A", meta1)
        target.write("skill-b", "# Skill B\n\nContent B", meta2)
        count = target.finalize()
        assert count == 2

        content = out.read_text()
        assert "Skill A" in content
        assert "Skill B" in content

    def test_default_output_path(self):
        target = CopilotTarget()
        assert target.output_path == Path(".github/copilot-instructions.md")


# ── AgentsMdTarget 测试 ──────────────────────────────────────────


class TestAgentsMdTarget:
    def test_write_and_finalize(self, tmp_path):
        out = tmp_path / "AGENTS.md"
        target = AgentsMdTarget(output_path=str(out))

        meta = {"name": "TDD", "summary": "测试驱动"}
        target.write("tdd", SAMPLE_SKILL_CONTENT, meta)
        count = target.finalize()
        assert count == 1
        assert out.exists()
        content = out.read_text()
        assert "Generated by Skills Orchestrator" in content
        assert "测试驱动开发" in content

    def test_content_with_frontmatter_preserved(self, tmp_path):
        out = tmp_path / "AGENTS.md"
        target = AgentsMdTarget(output_path=str(out))

        meta = {"name": "TDD", "summary": "测试驱动"}
        target.write("tdd", SAMPLE_SKILL_CONTENT, meta)
        target.finalize()

        content = out.read_text()
        # frontmatter 保留
        assert "---" in content

    def test_content_without_frontmatter_wrapped(self, tmp_path):
        out = tmp_path / "AGENTS.md"
        target = AgentsMdTarget(output_path=str(out))

        meta = {"name": "风格", "summary": "代码风格"}
        target.write("code-style", SAMPLE_SKILL_NO_FM, meta)
        target.finalize()

        content = out.read_text()
        # 无 frontmatter 的内容被 --- 包裹
        assert "---" in content
        assert "代码风格规范" in content

    def test_finalize_overwrites_manual_changes(self, tmp_path):
        """sync 是生成式覆盖：目标文件的手工修改不会被保留。"""
        out = tmp_path / "AGENTS.md"
        meta = {"name": "TDD", "summary": "测试驱动"}

        target = AgentsMdTarget(output_path=str(out))
        target.write("tdd", SAMPLE_SKILL_CONTENT, meta)
        target.finalize()
        first_content = out.read_text(encoding="utf-8")

        out.write_text("manual edit\n", encoding="utf-8")

        target_again = AgentsMdTarget(output_path=str(out))
        target_again.write("tdd", SAMPLE_SKILL_CONTENT, meta)
        target_again.finalize()
        second_content = out.read_text(encoding="utf-8")

        assert second_content == first_content
        assert "manual edit" not in second_content


# ── SyncEngine 测试 ──────────────────────────────────────────────


class TestSyncEngine:
    def test_default_mode_forced_full_passive_summary(self, tmp_path):
        """默认模式：forced 完整内容 + passive 摘要"""
        # 创建一个临时 skill 文件
        skill_file = tmp_path / "tdd.md"
        skill_file.write_text(SAMPLE_SKILL_CONTENT, encoding="utf-8")

        forced = [
            _make_skill(
                "tdd", "TDD", "测试驱动", ["testing"], path=str(skill_file), load_policy="require"
            )
        ]
        passive = [_make_skill("code-style", "风格", "命名约定", ["style"], load_policy="free")]
        resolved = _make_resolved(forced=forced, passive=passive)

        # 用 mock target 记录写入
        class MockTarget(SyncTarget):
            def __init__(self):
                self.writes = []

            @property
            def name(self):
                return "mock"

            def write(self, skill_id, content, meta):
                self.writes.append((skill_id, content, meta))

            def finalize(self):
                return len(self.writes)

        target = MockTarget()
        engine = SyncEngine(resolved, full=False)
        count = engine.sync_to(target)
        assert count == 2
        assert target.writes[0][0] == "tdd"
        assert "测试驱动开发" in target.writes[0][1]  # 完整内容
        assert target.writes[1][0] == "code-style"
        assert "如需完整内容" in target.writes[1][1]  # 摘要

    def test_full_mode_all_complete(self, tmp_path):
        """--full 模式：所有 skill 完整内容"""
        skill_file = tmp_path / "tdd.md"
        skill_file.write_text(SAMPLE_SKILL_CONTENT, encoding="utf-8")

        forced = [
            _make_skill(
                "tdd", "TDD", "测试驱动", ["testing"], path=str(skill_file), load_policy="require"
            )
        ]
        passive = [_make_skill("code-style", "风格", "命名约定", ["style"], load_policy="free")]
        resolved = _make_resolved(forced=forced, passive=passive)

        class MockTarget(SyncTarget):
            def __init__(self):
                self.writes = []

            @property
            def name(self):
                return "mock"

            def write(self, skill_id, content, meta):
                self.writes.append((skill_id, content, meta))

            def finalize(self):
                return len(self.writes)

        target = MockTarget()
        engine = SyncEngine(resolved, full=True)
        count = engine.sync_to(target)
        assert count == 2
        # 两个都是完整内容（被动的不应有摘要标记）
        assert "如需完整内容" not in target.writes[1][1]

    def test_missing_skill_file_graceful(self):
        """skill 文件不存在时不崩溃"""
        forced = [
            _make_skill(
                "missing",
                "Missing",
                "不存在",
                ["test"],
                path="/nonexistent/skill.md",
                load_policy="require",
            )
        ]
        resolved = _make_resolved(forced=forced)

        class MockTarget(SyncTarget):
            def __init__(self):
                self.writes = []

            @property
            def name(self):
                return "mock"

            def write(self, skill_id, content, meta):
                self.writes.append((skill_id, content, meta))

            def finalize(self):
                return len(self.writes)

        target = MockTarget()
        engine = SyncEngine(resolved, full=False)
        count = engine.sync_to(target)
        assert count == 1
        assert "文件不存在" in target.writes[0][1]

    def test_blocked_skills_excluded(self):
        """blocked skills 不参与同步"""
        forced = [_make_skill("a", "A", "s", [], load_policy="require")]
        blocked = [_make_skill("b", "B", "blocked", [], load_policy="require")]
        resolved = _make_resolved(forced=forced, blocked=blocked)

        class MockTarget(SyncTarget):
            def __init__(self):
                self.writes = []

            @property
            def name(self):
                return "mock"

            def write(self, skill_id, content, meta):
                self.writes.append((skill_id, content, meta))

            def finalize(self):
                return len(self.writes)

        target = MockTarget()
        engine = SyncEngine(resolved, full=False)
        count = engine.sync_to(target)
        assert count == 1
        assert target.writes[0][0] == "a"

    def test_prepare_called_before_write(self, tmp_path):
        """sync_to 会先调用 prepare"""
        skill_file = tmp_path / "a.md"
        skill_file.write_text("# A", encoding="utf-8")

        forced = [_make_skill("a", "A", "s", [], path=str(skill_file), load_policy="require")]
        resolved = _make_resolved(forced=forced, base_dir=str(tmp_path))

        call_order = []

        class MockTarget(SyncTarget):
            @property
            def name(self):
                return "mock"

            def prepare(self):
                call_order.append("prepare")

            def write(self, skill_id, content, meta):
                call_order.append("write")

            def finalize(self):
                return 1

        target = MockTarget()
        engine = SyncEngine(resolved)
        engine.sync_to(target)
        assert call_order[0] == "prepare"
        assert "write" in call_order


# ── CLI 集成测试（dry-run 模式，不写文件）──────────────────────


class TestSyncCLI:
    def test_sync_dry_run_hermes(self):
        """dry-run 不应创建任何文件"""
        import subprocess

        result = subprocess.run(
            ["skills-orchestrator", "sync", "hermes", "--dry-run"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0
        assert "[dry-run]" in result.stdout

    def test_sync_dry_run_openclaw(self):
        import subprocess

        result = subprocess.run(
            ["skills-orchestrator", "sync", "openclaw", "--dry-run"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0
        assert "[dry-run]" in result.stdout

    def test_sync_dry_run_copilot(self):
        import subprocess

        result = subprocess.run(
            ["skills-orchestrator", "sync", "copilot", "--dry-run"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0
        assert "[dry-run]" in result.stdout

    def test_sync_unknown_target_fails(self):
        import subprocess

        result = subprocess.run(
            ["skills-orchestrator", "sync", "nonexistent"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode != 0


class TestSyncEngineInheritance:
    """验证 SyncEngine._read_skill_content 走 registry.get_content() 合并继承内容"""

    def test_read_skill_content_with_registry(self, tmp_path):
        """有 registry 时，_read_skill_content 应返回合并后的内容"""
        from unittest.mock import MagicMock

        child = _make_skill(
            "child", "Child", "child summary", ["core"], path=str(tmp_path / "child.md")
        )

        resolved = _make_resolved([child], [], [])

        # mock registry: get_content("child") 返回合并后的内容
        registry = MagicMock()
        registry.get_content.return_value = (
            "---\nid: parent\n---\n\nParent body\n\n---\n\nChild body"
        )

        engine = SyncEngine(resolved, registry=registry)
        content = engine._read_skill_content(child)

        registry.get_content.assert_called_once_with("child")
        assert "Parent body" in content
        assert "Child body" in content

    def test_read_skill_content_without_registry_falls_back(self, tmp_path):
        """无 registry 时，降级为直接读文件"""
        skill_file = tmp_path / "test.md"
        skill_file.write_text("---\nid: test\n---\n\nRaw content")

        skill = _make_skill("test", "Test", "test", ["core"], path=str(skill_file))
        resolved = _make_resolved([skill], [], [])

        engine = SyncEngine(resolved)  # 不传 registry
        content = engine._read_skill_content(skill)

        assert "Raw content" in content

    def test_read_skill_content_registry_failure_falls_back(self, tmp_path):
        """registry.get_content 抛异常时，降级为文件直读"""
        from unittest.mock import MagicMock

        skill_file = tmp_path / "test.md"
        skill_file.write_text("---\nid: test\n---\n\nFallback content")

        skill = _make_skill("test", "Test", "test", ["core"], path=str(skill_file))
        resolved = _make_resolved([skill], [], [])

        registry = MagicMock()
        registry.get_content.side_effect = RuntimeError("boom")

        engine = SyncEngine(resolved, registry=registry)
        content = engine._read_skill_content(skill)

        assert "Fallback content" in content
