"""MCP 模块测试 — Registry、Search、Tools"""

from pathlib import Path
import pytest

from src.models import SkillMeta
from src.mcp.search import KeywordSearcher
from src.mcp.registry import SkillRegistry
from src.mcp.tools import ToolExecutor


# ── 测试 fixtures ────────────────────────────────────────────────


def _make_skill(id, name, summary, tags, priority=50):
    return SkillMeta(
        id=id,
        name=name,
        path=f"/fake/{id}.md",
        summary=summary,
        tags=tags,
        load_policy="free",
        priority=priority,
        zones=["default"],
        conflict_with=[],
    )


SAMPLE_SKILLS = [
    _make_skill(
        "git-worktrees",
        "Git Worktrees 工作流",
        "同时在多个分支工作，无需 stash 或切换分支",
        ["git", "workflow", "parallel"],
        80,
    ),
    _make_skill(
        "git-operations", "Git 操作规范", "提交信息格式、分支命名约定", ["git", "base"], 50
    ),
    _make_skill(
        "karpathy-guidelines",
        "Karpathy Guidelines",
        "减少 LLM 编码错误：简洁、外科式修改、目标驱动",
        ["coding", "quality", "mindset"],
        150,
    ),
    _make_skill(
        "brainstorming",
        "结构化头脑风暴",
        "发散收敛，避免过早收敛到第一个方案",
        ["planning", "design"],
        70,
    ),
    _make_skill(
        "finish-branch",
        "完成分支清单",
        "提 PR 前的检查清单：代码、测试、commit、文档",
        ["git", "pr", "checklist"],
        80,
    ),
]


# ── KeywordSearcher 测试 ─────────────────────────────────────────


class TestKeywordSearcher:
    def setup_method(self):
        self.searcher = KeywordSearcher()

    def test_exact_tag_match(self):
        results = self.searcher.search("git", SAMPLE_SKILLS, top_k=5)
        ids = [r.skill.id for r in results]
        assert "git-worktrees" in ids
        assert "git-operations" in ids

    def test_semantic_keyword_match(self):
        results = self.searcher.search("branch parallel work", SAMPLE_SKILLS, top_k=3)
        assert results[0].skill.id == "git-worktrees"

    def test_chinese_query(self):
        results = self.searcher.search("分支 并行", SAMPLE_SKILLS, top_k=3)
        ids = [r.skill.id for r in results]
        assert "git-worktrees" in ids

    def test_top_k_respected(self):
        results = self.searcher.search("git", SAMPLE_SKILLS, top_k=2)
        assert len(results) <= 2

    def test_empty_query_returns_all(self):
        results = self.searcher.search("", SAMPLE_SKILLS, top_k=10)
        assert len(results) == len(SAMPLE_SKILLS)

    def test_no_match_returns_empty(self):
        results = self.searcher.search("xyznonexistent", SAMPLE_SKILLS, top_k=5)
        assert len(results) == 0

    def test_scores_in_valid_range(self):
        results = self.searcher.search("git workflow", SAMPLE_SKILLS)
        for r in results:
            assert 0.0 <= r.score <= 1.0

    def test_matched_fields_populated(self):
        results = self.searcher.search("git-worktrees parallel", SAMPLE_SKILLS, top_k=1)
        assert len(results) > 0
        assert len(results[0].matched_fields) > 0


# ── ToolExecutor 测试 ────────────────────────────────────────────


class MockRegistry:
    """不依赖文件系统的 Registry mock"""

    def all(self):
        return SAMPLE_SKILLS

    def combos(self):
        from src.models import Combo

        return [
            Combo(
                id="git-workflow",
                name="Git 工作流套件",
                members=["git-operations", "git-worktrees", "finish-branch"],
                description="Git 基础操作 + Worktrees + 完成分支清单",
            ),
        ]

    def get_meta(self, skill_id):
        return next((s for s in SAMPLE_SKILLS if s.id == skill_id), None)

    def get_content(self, skill_id):
        meta = self.get_meta(skill_id)
        if meta is None:
            return None
        return f"# {meta.name}\n\n{meta.summary}\n"


class TestToolExecutor:
    def setup_method(self):
        self.executor = ToolExecutor(MockRegistry())

    def _text(self, results) -> str:
        return "\n".join(r.text for r in results)

    # list_skills
    def test_list_skills_all(self):
        results = self.executor.execute("list_skills", {})
        text = self._text(results)
        assert "git-worktrees" in text
        assert "karpathy-guidelines" in text

    def test_list_skills_tag_filter(self):
        results = self.executor.execute("list_skills", {"tag": "git"})
        text = self._text(results)
        assert "git-worktrees" in text
        assert "brainstorming" not in text

    def test_list_skills_unknown_tag(self):
        results = self.executor.execute("list_skills", {"tag": "nonexistent"})
        text = self._text(results)
        assert "没有找到" in text

    # search_skills
    def test_search_skills_returns_ranked(self):
        results = self.executor.execute("search_skills", {"query": "git branch parallel"})
        text = self._text(results)
        assert "git-worktrees" in text
        assert "相关度" in text

    def test_search_skills_empty_query(self):
        results = self.executor.execute("search_skills", {"query": ""})
        text = self._text(results)
        assert "请提供" in text

    # get_skill
    def test_get_skill_returns_content(self):
        results = self.executor.execute("get_skill", {"id": "karpathy-guidelines"})
        text = self._text(results)
        assert "Karpathy Guidelines" in text
        assert "减少 LLM 编码错误" in text

    def test_get_skill_not_found(self):
        results = self.executor.execute("get_skill", {"id": "nonexistent-skill"})
        text = self._text(results)
        assert "找不到" in text

    def test_get_skill_suggests_similar(self):
        results = self.executor.execute("get_skill", {"id": "git-work"})
        text = self._text(results)
        # 应提示相似 id
        assert "git-worktrees" in text

    # suggest_combo
    def test_suggest_combo_returns_plans(self):
        results = self.executor.execute(
            "suggest_combo", {"requirement": "部署微服务，需要 git 工作流和代码审查"}
        )
        text = self._text(results)
        assert "方案" in text
        assert "Skills:" in text

    def test_suggest_combo_empty_requirement(self):
        results = self.executor.execute("suggest_combo", {"requirement": ""})
        text = self._text(results)
        assert "请描述" in text

    # 未知工具
    def test_unknown_tool(self):
        results = self.executor.execute("unknown_tool", {})
        text = self._text(results)
        assert "未知工具" in text


# ── SkillRegistry 集成测试（真实文件）───────────────────────────


class TestSkillRegistryIntegration:
    @pytest.fixture
    def registry(self):
        project_root = Path(__file__).parent.parent
        config_path = project_root / "config" / "skills.yaml"
        if not config_path.exists():
            pytest.skip("配置文件不存在")
        return SkillRegistry(str(config_path))

    def test_loads_skills(self, registry):
        skills = registry.all()
        assert len(skills) >= 10

    def test_get_content_returns_markdown(self, registry):
        skills = registry.all()
        content = registry.get_content(skills[0].id)
        assert content is not None
        assert len(content) > 50

    def test_get_meta_returns_skill(self, registry):
        skills = registry.all()
        meta = registry.get_meta(skills[0].id)
        assert meta is not None
        assert meta.id == skills[0].id

    def test_unknown_id_returns_none(self, registry):
        assert registry.get_content("totally-fake-skill-xyz") is None

    def test_reload_works(self, registry):
        registry.reload()
        assert len(registry.all()) >= 10


# ── SkillRegistry 继承 (base skill) 单元测试 ────────────────────


class TestSkillRegistryInheritance:
    """get_content 对 base 字段的合并行为"""

    def _make_registry_with_skills(self, tmp_path, skill_files: dict[str, str]) -> SkillRegistry:
        """在 tmp_path 创建 .md 文件并生成临时 skills.yaml，返回 SkillRegistry。"""
        for fname, content in skill_files.items():
            (tmp_path / fname).write_text(content)

        yaml_content = f"""
version: "1.0"
zones:
  - id: default
    name: 默认区
    load_policy: free
    priority: 0
    rules: []
skill_dirs:
  - {str(tmp_path)}
"""
        config_file = tmp_path / "skills.yaml"
        config_file.write_text(yaml_content)
        return SkillRegistry(str(config_file))

    def test_no_base_returns_raw_content(self, tmp_path):
        reg = self._make_registry_with_skills(
            tmp_path,
            {
                "plain.md": "---\nid: plain\nname: Plain\nsummary: s\n---\n# Plain Content\n",
            },
        )
        content = reg.get_content("plain")
        assert "# Plain Content" in content

    def test_base_content_prepended(self, tmp_path):
        """derived skill 的内容应拼接在 base 内容后面"""
        reg = self._make_registry_with_skills(
            tmp_path,
            {
                "base.md": "---\nid: base\nname: Base\nsummary: s\n---\n# Base Rules\n",
                "derived.md": "---\nid: derived\nname: Derived\nsummary: s\nbase: base\n---\n# Derived Extensions\n",
            },
        )
        content = reg.get_content("derived")
        assert "# Base Rules" in content
        assert "# Derived Extensions" in content
        # base 应该在 derived 之前
        assert content.index("# Base Rules") < content.index("# Derived Extensions")

    def test_base_frontmatter_not_duplicated(self, tmp_path):
        """base 的 frontmatter 出现一次，derived 的 frontmatter 被剥离"""
        reg = self._make_registry_with_skills(
            tmp_path,
            {
                "base.md": "---\nid: base\nname: Base\nsummary: s\n---\n# Base\n",
                "derived.md": "---\nid: derived\nname: Derived\nsummary: s\nbase: base\n---\n# Derived\n",
            },
        )
        content = reg.get_content("derived")
        # derived 的 frontmatter 应被剥离（不应出现两个 "id: derived"）
        assert content.count("id: derived") == 0

    def test_warm_cache_respects_base(self, tmp_path):
        """forced skill (load_policy: require) 有 base 时，预热缓存不应绕过合并逻辑"""
        reg = self._make_registry_with_skills(
            tmp_path,
            {
                "base.md": "---\nid: base\nname: Base\nsummary: s\n---\n# Base Rules\n",
                "forced.md": (
                    "---\nid: forced\nname: Forced\nsummary: s\n"
                    "load_policy: require\nbase: base\n---\n# Forced Extensions\n"
                ),
            },
        )
        # forced skill 在 _load() 时被 _warm() 预热，get_content 命中缓存后应仍包含 base 内容
        content = reg.get_content("forced")
        assert "# Base Rules" in content
        assert "# Forced Extensions" in content

    def test_chain_inheritance(self, tmp_path):
        """三级继承：A → B → C，内容正确合并"""
        reg = self._make_registry_with_skills(
            tmp_path,
            {
                "c.md": "---\nid: c\nname: C\nsummary: s\n---\n# C Content\n",
                "b.md": "---\nid: b\nname: B\nsummary: s\nbase: c\n---\n# B Content\n",
                "a.md": "---\nid: a\nname: A\nsummary: s\nbase: b\n---\n# A Content\n",
            },
        )
        content = reg.get_content("a")
        assert "# C Content" in content
        assert "# B Content" in content
        assert "# A Content" in content
        assert (
            content.index("# C Content")
            < content.index("# B Content")
            < content.index("# A Content")
        )
