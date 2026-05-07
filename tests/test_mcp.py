"""MCP 模块测试 — Registry、Search、Tools"""

from pathlib import Path
import pytest

from skills_orchestrator.models import SkillMeta
from skills_orchestrator.mcp.search import KeywordSearcher
from skills_orchestrator.mcp.registry import SkillRegistry
from skills_orchestrator.mcp.tools import ALL_TOOLS, ToolExecutor


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

    def forced(self):
        return [s for s in SAMPLE_SKILLS if s.load_policy == "require"]

    def passive(self):
        return [s for s in SAMPLE_SKILLS if s.load_policy != "require"]

    def combos(self):
        from skills_orchestrator.models import Combo

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
    def test_execute_rejects_non_object_arguments(self):
        with pytest.raises(ValueError, match="JSON object"):
            self.executor.execute("list_skills", [])

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

    def test_list_skills_rejects_non_string_tag(self):
        with pytest.raises(ValueError, match="tag"):
            self.executor.execute("list_skills", {"tag": 123})

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

    def test_search_skills_rejects_non_string_query(self):
        with pytest.raises(ValueError, match="query"):
            self.executor.execute("search_skills", {"query": 123})

    def test_search_skills_rejects_non_numeric_top_k(self):
        with pytest.raises(ValueError, match="top_k"):
            self.executor.execute("search_skills", {"query": "git", "top_k": "many"})

    def test_search_skills_clamps_large_top_k(self):
        results = self.executor.execute("search_skills", {"query": "git", "top_k": 999})
        text = self._text(results)
        assert "git-worktrees" in text

    # get_skill
    def test_get_skill_returns_content(self):
        results = self.executor.execute("get_skill", {"id": "karpathy-guidelines"})
        text = self._text(results)
        assert "Karpathy Guidelines" in text
        assert "减少 LLM 编码错误" in text

    def test_get_skill_not_found(self):
        with pytest.raises(ValueError) as exc_info:
            self.executor.execute("get_skill", {"id": "nonexistent-skill"})
        assert "找不到" in str(exc_info.value)

    def test_get_skill_suggests_similar(self):
        with pytest.raises(ValueError) as exc_info:
            self.executor.execute("get_skill", {"id": "git-work"})
        # 应提示相似 id
        assert "git-worktrees" in str(exc_info.value)

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

    def test_suggest_combo_rejects_non_numeric_max_combos(self):
        with pytest.raises(ValueError, match="max_combos"):
            self.executor.execute("suggest_combo", {"requirement": "git", "max_combos": "many"})

    # prepare_context
    def test_prepare_context_is_exposed(self):
        assert "prepare_context" in {tool.name for tool in ALL_TOOLS}

    def test_prepare_context_returns_active_skills_and_content(self):
        results = self.executor.execute(
            "prepare_context",
            {"task": "需要 git 分支并行工作和提交规范", "max_skills": 2},
        )
        text = self._text(results)
        assert "Prepared Context" in text
        assert "active_skills:" in text
        assert "git-worktrees" in text
        assert "inactive_skills:" in text
        assert "本任务只遵循 active_skills" in text
        assert "Active Skill Content" in text
        assert "# Git Worktrees 工作流" in text

    def test_prepare_context_can_return_summary_only(self):
        results = self.executor.execute(
            "prepare_context",
            {"task": "git workflow", "max_skills": 2, "include_content": False},
        )
        text = self._text(results)
        assert "active_skills:" in text
        assert "Active Skill Content" not in text
        assert "使用 `get_skill(id)`" in text

    def test_prepare_context_empty_task(self):
        results = self.executor.execute("prepare_context", {"task": ""})
        text = self._text(results)
        assert "请提供 task" in text

    def test_prepare_context_rejects_non_string_task(self):
        with pytest.raises(ValueError, match="task"):
            self.executor.execute("prepare_context", {"task": 123})

    def test_prepare_context_rejects_non_numeric_max_skills(self):
        with pytest.raises(ValueError, match="max_skills"):
            self.executor.execute("prepare_context", {"task": "git", "max_skills": "many"})

    def test_prepare_context_rejects_non_boolean_include_content(self):
        with pytest.raises(ValueError, match="include_content"):
            self.executor.execute(
                "prepare_context",
                {"task": "git", "include_content": "yes"},
            )

    def test_prepare_context_required_skills_always_in_active(self, tmp_path):
        """required skills 必须无条件进入 active_skills，即使任务与之无关。"""
        skill_dir = tmp_path / "skills"
        skill_dir.mkdir()
        (skill_dir / "security-check.md").write_text(
            "---\nid: security-check\nname: Security Check\n"
            "summary: 安全审查，所有变更必须通过\nload_policy: require\n"
            "priority: 90\ntags: [security]\n---\n# Security\n",
            encoding="utf-8",
        )
        (skill_dir / "sorting.md").write_text(
            "---\nid: sorting\nname: Sorting Algorithms\n"
            "summary: 排序算法实现\nload_policy: free\n"
            "priority: 50\ntags: [algorithm]\n---\n# Sort\n",
            encoding="utf-8",
        )
        cfg = tmp_path / "skills.yaml"
        cfg.write_text(f"skill_dirs:\n  - skills\nzones: []\n", encoding="utf-8")

        from skills_orchestrator.mcp.registry import SkillRegistry
        from skills_orchestrator.mcp.tools import ToolExecutor

        registry = SkillRegistry(str(cfg))
        executor = ToolExecutor(registry)

        # 任务与 security-check 完全无关，但 required skill 必须出现在 active_skills
        results = executor.execute(
            "prepare_context",
            {"task": "实现快速排序算法", "max_skills": 1, "include_content": False},
        )
        text = "\n".join(r.text for r in results)
        assert "security-check" in text, "required skill 必须出现在 active_skills"
        assert "REQUIRED" in text, "required skill 应有 [REQUIRED] 标记"
        assert "sorting" in text, "任务相关的 passive skill 也应出现"

    def test_pipeline_id_path_traversal_rejected(self, tmp_path):
        pipelines_dir = tmp_path / "pipelines"
        pipelines_dir.mkdir()
        outside = tmp_path / "evil.yaml"
        outside.write_text("id: evil\nname: Evil\nsteps: []\n", encoding="utf-8")

        executor = ToolExecutor(MockRegistry(), pipelines_dir=str(pipelines_dir))
        with pytest.raises(ValueError, match="pipeline_id"):
            executor.execute("pipeline_start", {"pipeline_id": "../evil"})

    def test_pipeline_start_rejects_non_object_context(self):
        with pytest.raises(ValueError, match="context"):
            self.executor.execute("pipeline_start", {"pipeline_id": "missing", "context": "bad"})

    def test_pipeline_advance_rejects_non_object_context_updates(self):
        with pytest.raises(ValueError, match="context_updates"):
            self.executor.execute(
                "pipeline_advance",
                {"pipeline_id": "full-dev", "run_id": "run-1", "context_updates": []},
            )

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


class TestSkillRegistryZoneIsolation:
    """测试 Zone 隔离：get_content 不能绕过 Zone 读取隐藏 skill"""

    def _make_registry_with_zone(
        self, tmp_path, skills: dict[str, str], zone_skills: list[str], zone_id: str = "enterprise"
    ) -> SkillRegistry:
        """创建带 zone 的 Registry（使用 skill_dirs）

        Args:
            tmp_path: 临时目录
            skills: {filename: content} 文件内容映射
            zone_skills: 该 zone 可见的 skill id 列表
            zone_id: zone id
        """
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        for filename, content in skills.items():
            (skills_dir / filename).write_text(content)

        # 生成 skills.yaml（使用 skill_dirs）
        skills_yaml = tmp_path / "config" / "skills.yaml"
        skills_yaml.parent.mkdir(parents=True, exist_ok=True)

        zone_skill_ids = "\n".join([f"      - {sid}" for sid in zone_skills])
        yaml_content = f"""version: "1.0"
zones:
  - id: {zone_id}
    name: Enterprise Zone
    load_policy: free
    priority: 100
    skills:
{zone_skill_ids}
skill_dirs:
  - {str(skills_dir)}
"""
        skills_yaml.write_text(yaml_content)

        return SkillRegistry(str(skills_yaml), zone_id=zone_id)

    def test_get_content_zone_isolation(self, tmp_path):
        """Zone 隔离：不能读取 zone 外的 skill"""
        reg = self._make_registry_with_zone(
            tmp_path,
            {
                "tdd.md": "---\nid: tdd\nname: TDD\nsummary: Test-Driven Development\n---\n# TDD",
                "enterprise.md": "---\nid: enterprise\nname: Enterprise\nsummary: Enterprise Skill\n---\n# Enterprise",
            },
            zone_skills=["enterprise"],  # 只有 enterprise 在 zone 内
        )

        # list_skills 只能看到 enterprise
        all_skills = reg.all()
        assert len(all_skills) == 1
        assert all_skills[0].id == "enterprise"

        # get_meta 只能拿到 enterprise
        assert reg.get_meta("enterprise") is not None
        assert reg.get_meta("tdd") is None

        # get_content 只能拿到 enterprise
        assert reg.get_content("enterprise") is not None
        assert reg.get_content("tdd") is None

    def test_base_inheritance_cross_zone(self, tmp_path):
        """跨 Zone base 继承：enterprise skill 可以继承 default zone 的 base"""
        reg = self._make_registry_with_zone(
            tmp_path,
            {
                "base.md": "---\nid: base\nname: Base\nsummary: Base Skill\n---\n# Base Content",
                "child.md": "---\nid: child\nname: Child\nsummary: Child Skill\nbase: base\n---\n# Child Content",
            },
            zone_skills=["child"],  # child 在 zone 内，base 不在
        )

        # get_content("child") 应该能读到 base 的内容（通过内部方法）
        content = reg.get_content("child")
        assert content is not None
        assert "# Base Content" in content
        assert "# Child Content" in content

        # 但 get_content("base") 应该返回 None（公共入口）
        assert reg.get_content("base") is None
