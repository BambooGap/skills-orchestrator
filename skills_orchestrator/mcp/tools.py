"""MCP Tool 定义 — list_skills / search_skills / get_skill / suggest_combo"""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

from mcp import types

from .registry import SkillRegistry
from .search import KeywordSearcher

if TYPE_CHECKING:
    from skills_orchestrator.pipeline.loader import Pipeline
    from skills_orchestrator.pipeline.store import RunStateStore


# ── Tool Schema 定义 ──────────────────────────────────────────────

TOOL_LIST_SKILLS = types.Tool(
    name="list_skills",
    description=(
        "列出所有可用的 skill。返回 id、名称、摘要、标签。用于了解有哪些技能可用，不加载完整内容。"
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "tag": {
                "type": "string",
                "description": "按标签过滤，如 'git'、'review'、'planning'。不传则返回全部。",
            }
        },
    },
)

TOOL_SEARCH_SKILLS = types.Tool(
    name="search_skills",
    description=(
        "根据自然语言描述搜索最相关的 skill。"
        "例如：'git branch parallel work'、'代码审查规范'、'调试 bug 步骤'。"
        "返回 Top-K 结果，按相关度排序。"
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "搜索需求，支持中英文混合",
            },
            "top_k": {
                "type": "integer",
                "description": "返回结果数量，默认 5",
                "default": 5,
            },
        },
        "required": ["query"],
    },
)

TOOL_GET_SKILL = types.Tool(
    name="get_skill",
    description=(
        "加载指定 skill 的完整内容。"
        "先用 list_skills 或 search_skills 找到需要的 skill id，再调用本工具加载完整指导内容。"
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "id": {
                "type": "string",
                "description": "Skill ID，如 'karpathy-guidelines'、'git-worktrees'",
            }
        },
        "required": ["id"],
    },
)

TOOL_SUGGEST_COMBO = types.Tool(
    name="suggest_combo",
    description=(
        "根据任务需求推荐最适合的 skill 组合方案。"
        "输入需求描述，返回 2-3 个组合方案，每个方案说明包含的 skill 及其优缺点。"
        "适合不确定该用哪些 skill 时调用。"
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "requirement": {
                "type": "string",
                "description": "任务或项目需求描述，越具体越好",
            },
            "max_combos": {
                "type": "integer",
                "description": "返回方案数量，默认 3",
                "default": 3,
            },
        },
        "required": ["requirement"],
    },
)

TOOL_PIPELINE_START = types.Tool(
    name="pipeline_start",
    description=(
        "启动一个预定义的 Pipeline 流程。"
        "Pipeline 是有序的 skill 步骤序列，包含质量门禁和自动跳过逻辑。"
        "例如：'full-dev' 完整开发流程、'quick-fix' 快速修复、'review-only' 仅审查。"
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "pipeline_id": {
                "type": "string",
                "description": "Pipeline ID，如 'full-dev'、'quick-fix'、'review-only'",
            },
            "context": {
                "type": "object",
                "description": '初始上下文，键值对。例如 {"scope_is_trivial": true} 可跳过构思阶段',
                "additionalProperties": True,
            },
        },
        "required": ["pipeline_id"],
    },
)

TOOL_PIPELINE_STATUS = types.Tool(
    name="pipeline_status",
    description=(
        "查看 Pipeline 运行状态：当前步骤、已完成步骤、门禁检查结果。"
        "不传 run_id 则返回最近一次运行的状态。"
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "run_id": {
                "type": "string",
                "description": "运行 ID。不传则查看最近一次运行。",
            },
            "pipeline_id": {
                "type": "string",
                "description": "Pipeline ID，配合 run_id 使用。",
            },
        },
    },
)

TOOL_PIPELINE_ADVANCE = types.Tool(
    name="pipeline_advance",
    description=(
        "推进 Pipeline 到下一步。当前步骤完成或跳过后调用。会自动执行门禁检查和质量验证。"
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "run_id": {
                "type": "string",
                "description": "运行 ID",
            },
            "pipeline_id": {
                "type": "string",
                "description": "Pipeline ID",
            },
            "artifacts": {
                "type": "array",
                "items": {"type": "string"},
                "description": "当前步骤产出的 artifact 键名列表，如 ['implementation_plan', 'code_changes']",
            },
            "context_updates": {
                "type": "object",
                "description": "上下文更新，键值对",
                "additionalProperties": True,
            },
        },
        "required": ["run_id", "pipeline_id"],
    },
)

TOOL_PIPELINE_RESUME = types.Tool(
    name="pipeline_resume",
    description=(
        "恢复中断的 Pipeline 运行。从中断点继续，或重试失败步骤。"
        "适用于上次运行因错误或手动停止后需要继续的场景。"
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "run_id": {
                "type": "string",
                "description": "运行 ID。不传则恢复最近一次中断的运行。",
            },
            "pipeline_id": {
                "type": "string",
                "description": "Pipeline ID",
            },
        },
    },
)

ALL_TOOLS = [
    TOOL_LIST_SKILLS,
    TOOL_SEARCH_SKILLS,
    TOOL_GET_SKILL,
    TOOL_SUGGEST_COMBO,
    TOOL_PIPELINE_START,
    TOOL_PIPELINE_STATUS,
    TOOL_PIPELINE_ADVANCE,
    TOOL_PIPELINE_RESUME,
]


# ── Tool 执行器 ───────────────────────────────────────────────────


class ToolExecutor:
    def __init__(self, registry: SkillRegistry, pipelines_dir: str | None = None):
        self._registry = registry
        self._searcher = KeywordSearcher()
        self._pipelines_dir = pipelines_dir
        self._pipelines: dict[str, Pipeline] = {}
        self._store: RunStateStore | None = None

    def _get_store(self) -> RunStateStore:
        from skills_orchestrator.pipeline.store import RunStateStore

        if self._store is None:
            self._store = RunStateStore()
        return self._store

    def _get_pipeline(self, pipeline_id: str) -> Pipeline | None:
        import os
        from skills_orchestrator.pipeline.loader import PipelineLoader

        if pipeline_id in self._pipelines:
            return self._pipelines[pipeline_id]

        loader = PipelineLoader()
        # 从内置 pipelines 目录查找
        pipelines_dir = self._pipelines_dir
        if pipelines_dir is None:
            pipelines_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config", "pipelines"
            )

        filepath = os.path.join(pipelines_dir, f"{pipeline_id}.yaml")
        if not os.path.exists(filepath):
            return None

        pipeline = loader.load(filepath)
        self._pipelines[pipeline_id] = pipeline
        return pipeline

    def execute(self, name: str, arguments: dict[str, Any]) -> list[types.TextContent]:
        handlers = {
            "list_skills": self._list_skills,
            "search_skills": self._search_skills,
            "get_skill": self._get_skill,
            "suggest_combo": self._suggest_combo,
            "pipeline_start": self._pipeline_start,
            "pipeline_status": self._pipeline_status,
            "pipeline_advance": self._pipeline_advance,
            "pipeline_resume": self._pipeline_resume,
        }
        handler = handlers.get(name)
        if handler is None:
            return [types.TextContent(type="text", text=f"未知工具: {name}")]
        return handler(arguments)

    # ── list_skills ───────────────────────────────────────────────

    def _list_skills(self, args: dict) -> list[types.TextContent]:
        tag_filter = args.get("tag", "").strip().lower()
        skills = self._registry.all()

        if tag_filter:
            skills = [s for s in skills if tag_filter in [t.lower() for t in s.tags]]

        if not skills:
            return [types.TextContent(type="text", text="没有找到匹配的 skill。")]

        rows = [f"共 {len(skills)} 个 skill：\n"]
        for s in skills:
            tags_str = ", ".join(s.tags)
            rows.append(f"• **{s.id}** — {s.name}")
            rows.append(f"  摘要: {s.summary}")
            rows.append(f"  标签: [{tags_str}]  优先级: {s.priority}")
            rows.append("")

        return [types.TextContent(type="text", text="\n".join(rows))]

    # ── search_skills ─────────────────────────────────────────────

    def _search_skills(self, args: dict) -> list[types.TextContent]:
        query = args.get("query", "").strip()
        top_k = int(args.get("top_k", 5))

        if not query:
            return [types.TextContent(type="text", text="请提供搜索关键词。")]

        results = self._searcher.search(query, self._registry.all(), top_k=top_k)

        if not results:
            return [types.TextContent(type="text", text=f"未找到与 '{query}' 相关的 skill。")]

        lines = [f"搜索 '{query}' 的结果（Top {len(results)}）：\n"]
        for i, r in enumerate(results, 1):
            s = r.skill
            score_pct = f"{r.score * 100:.0f}%"
            lines.append(f"{i}. **{s.id}** — {s.name}  [相关度 {score_pct}]")
            lines.append(f"   {s.summary}")
            lines.append(f"   命中字段: {', '.join(r.matched_fields)}")
            lines.append("")

        lines.append("使用 `get_skill(id)` 加载完整内容。")
        return [types.TextContent(type="text", text="\n".join(lines))]

    # ── get_skill ─────────────────────────────────────────────────

    def _get_skill(self, args: dict) -> list[types.TextContent]:
        skill_id = args.get("id", "").strip()

        if not skill_id:
            return [types.TextContent(type="text", text="请提供 skill id。")]

        content = self._registry.get_content(skill_id)
        meta = self._registry.get_meta(skill_id)

        if content is None:
            # 尝试模糊提示
            all_ids = [s.id for s in self._registry.all()]
            similar = [sid for sid in all_ids if skill_id.lower() in sid.lower()]
            hint = f"\n相似的 skill id: {', '.join(similar)}" if similar else ""
            return [
                types.TextContent(
                    type="text",
                    text=f"找不到 skill: '{skill_id}'{hint}\n使用 list_skills 查看所有可用 skill。",
                )
            ]

        header = (
            f"# Skill: {meta.name if meta else skill_id}\n"
            f"id: {skill_id} | "
            f"priority: {meta.priority if meta else '?'} | "
            f"tags: [{', '.join(meta.tags) if meta else ''}]\n\n"
            f"---\n\n"
        )
        return [types.TextContent(type="text", text=header + content)]

    # ── suggest_combo ─────────────────────────────────────────────

    def _suggest_combo(self, args: dict) -> list[types.TextContent]:
        requirement = args.get("requirement", "").strip()
        max_combos = int(args.get("max_combos", 3))

        if not requirement:
            return [types.TextContent(type="text", text="请描述你的任务需求。")]

        # 获取可用 skill id 集合（registry 只含非 blocked skills）
        available_ids = {s.id for s in self._registry.all()}

        candidates = self._searcher.search(requirement, self._registry.all(), top_k=10)

        if not candidates:
            return [
                types.TextContent(
                    type="text",
                    text="未找到与需求相关的 skill，建议先用 search_skills 确认关键词。",
                )
            ]

        combos = self._build_combos(candidates, requirement, max_combos, available_ids)

        lines = [f"根据需求「{requirement}」推荐以下方案：\n"]
        for i, combo in enumerate(combos, 1):
            lines.append(f"## 方案 {i}：{combo['name']}")
            if combo.get("description"):
                lines.append(f"说明：{combo['description']}")
            lines.append(f"Skills: {', '.join(combo['skills'])}")
            lines.append(f"适用：{combo['pros']}")
            lines.append(f"注意：{combo['cons']}")
            lines.append("")

        lines.append("使用 `get_skill(id)` 加载方案中任意 skill 的完整内容。")
        return [types.TextContent(type="text", text="\n".join(lines))]

    def _build_combos(
        self,
        candidates: list,
        requirement: str,
        max_combos: int,
        available_ids: set[str] | None = None,
    ) -> list[dict]:
        """优先返回匹配的预定义 combo，不足时动态构建补充。

        available_ids: 可用 skill id 集合，用于过滤 blocked skills。
        """
        if available_ids is None:
            available_ids = {s.skill.id for s in candidates}

        candidate_ids = {r.skill.id for r in candidates}
        all_skills = [r.skill for r in candidates]

        combos: list[dict] = []

        # 1. 优先：预定义 combo（成员与候选集有交集的，且排除 blocked 成员）
        for predefined in self._registry.combos():
            # 过滤掉 blocked skills
            valid_members = [m for m in predefined.members if m in available_ids]
            if not valid_members:
                continue  # combo 所有成员都被 blocked，跳过

            overlap = [m for m in valid_members if m in candidate_ids]
            if overlap and len(combos) < max_combos:
                combos.append(
                    {
                        "name": predefined.name,
                        "description": predefined.description,
                        "skills": valid_members,  # 只返回可用成员
                        "pros": predefined.description or "预定义的经过验证的 skill 组合",
                        "cons": "按固定组合加载，灵活性较低"
                        + (
                            " (部分成员已被拦截)"
                            if len(valid_members) < len(predefined.members)
                            else ""
                        ),
                    }
                )

        # 2. 补充：动态构建（不足 max_combos 时）
        if len(combos) < max_combos:
            top = all_skills[:3]
            mid = all_skills[3:6] if len(all_skills) > 3 else []

            if top and len(combos) < max_combos:
                combos.append(
                    {
                        "name": "轻量快速版",
                        "description": "",
                        "skills": [s.id for s in top[:2]],
                        "pros": "技能数量少，上手快，适合独立开发者或小团队",
                        "cons": "覆盖面有限，复杂项目可能需要补充其他 skill",
                    }
                )

            if top and mid and len(combos) < max_combos:
                combos.append(
                    {
                        "name": "完整流程版",
                        "description": "",
                        "skills": [s.id for s in (top + mid)[:4]],
                        "pros": "覆盖从规划到上线的完整流程，减少返工",
                        "cons": "需要团队成员熟悉多个规范，初期有一定学习成本",
                    }
                )

            if len(combos) < max_combos:
                git_skills = [s for s in all_skills if "git" in s.tags][:2]
                review_skills = [s for s in all_skills if "review" in s.tags][:1]
                plan_skills = [s for s in all_skills if "planning" in s.tags][:1]
                balanced = git_skills + review_skills + plan_skills
                if len(balanced) >= 2:
                    combos.append(
                        {
                            "name": "均衡领域版",
                            "description": "",
                            "skills": [s.id for s in balanced],
                            "pros": "各领域均衡覆盖：流程规范 + 代码质量 + 工作流管理",
                            "cons": "通用性强但针对性略弱，可根据实际情况调整",
                        }
                    )

        return combos[:max_combos]

    # ── pipeline_start ────────────────────────────────────────────

    def _pipeline_start(self, args: dict) -> list[types.TextContent]:
        import os
        from skills_orchestrator.pipeline.engine import PipelineEngine

        pipeline_id = args.get("pipeline_id", "").strip()
        context = args.get("context", {})

        if not pipeline_id:
            # 列出可用的 pipeline
            pipelines_dir = self._pipelines_dir or os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config", "pipelines"
            )
            available = []
            if os.path.isdir(pipelines_dir):
                for f in sorted(os.listdir(pipelines_dir)):
                    if f.endswith(".yaml"):
                        available.append(f.replace(".yaml", ""))
            return [
                types.TextContent(
                    type="text",
                    text=f"请提供 pipeline_id。可用的 Pipeline：{', '.join(available) or '无'}",
                )
            ]

        pipeline = self._get_pipeline(pipeline_id)
        if pipeline is None:
            return [types.TextContent(type="text", text=f"找不到 Pipeline: '{pipeline_id}'")]

        # 校验 pipeline 引用的 skill 是否存在于 registry
        from skills_orchestrator.pipeline.loader import PipelineLoader

        loader = PipelineLoader()
        known_skills = {s.id for s in self._registry.all()}
        missing = loader.validate_skills(pipeline, known_skills)
        if missing:
            return [
                types.TextContent(
                    type="text",
                    text=f"Pipeline '{pipeline_id}' 引用了不存在的 skill: {', '.join(missing)}\n"
                    f"可用 skill: {', '.join(sorted(known_skills))}\n"
                    f"请修复 config/pipelines/{pipeline_id}.yaml 中的 skill 引用。",
                )
            ]

        engine = PipelineEngine(pipeline)
        state = engine.start(context=context)
        self._get_store().save(state)

        step = pipeline.get_step(state.current_step) if state.current_step else None
        lines = [
            f"Pipeline '{pipeline.name}' 已启动！",
            f"Run ID: {state.run_id}",
            f"当前步骤: {state.current_step} (skill: {step.skill if step else '?'})",
            f"状态: {state.status}",
            "",
            "后续步骤：",
        ]
        for s in pipeline.steps:
            marker = " > " if s.id == state.current_step else "   "
            skip_note = f" [可跳过: {s.skip_if}]" if s.skip_if else ""
            gate_note = f" [门禁: {s.gate.must_produce}]" if s.gate else ""
            lines.append(f"{marker}{s.id} → {s.skill}{skip_note}{gate_note}")

        # 注入当前步骤的 skill 完整内容到上下文
        if step and self._registry is not None:
            skill_content = self._registry.get_content(step.skill)
            if skill_content:
                lines.append("")
                lines.append(f"═══ 当前步骤 Skill: {step.skill} ═══")
                lines.append(skill_content)
                lines.append("═══════════════════════════════════")

        # 注入门禁要求提示
        if step and step.gate:
            lines.append("")
            lines.append(f"⚠ 门禁要求: 完成此步骤前必须产出 '{step.gate.must_produce}'")
            if step.gate.min_length:
                lines.append(f"  最小长度: {step.gate.min_length} 字符")

        lines.append("")
        lines.append(
            f"使用 pipeline_advance(run_id='{state.run_id}', pipeline_id='{pipeline_id}') 推进下一步。"
        )
        return [types.TextContent(type="text", text="\n".join(lines))]

    # ── pipeline_status ──────────────────────────────────────────

    def _pipeline_status(self, args: dict) -> list[types.TextContent]:
        run_id = args.get("run_id", "").strip()
        pipeline_id = args.get("pipeline_id", "").strip()

        store = self._get_store()

        if run_id and pipeline_id:
            state = store.load(pipeline_id, run_id)
        else:
            state = store.load_latest(pipeline_id or None)

        if state is None:
            return [types.TextContent(type="text", text="没有找到运行记录。")]

        pipeline = self._get_pipeline(state.pipeline_id)
        lines = [
            f"Pipeline: {state.pipeline_id}  Run: {state.run_id}",
            f"状态: {state.status}  当前步骤: {state.current_step or '(已完成)'}",
            f"开始时间: {state.started_at}  更新时间: {state.updated_at}",
            "",
            "步骤历史：",
        ]
        for h in state.step_history:
            status_icon = {"completed": "✓", "skipped": "⏭", "failed": "✗"}.get(h["status"], "?")
            reason = f" ({h.get('reason', '')})" if h.get("reason") else ""
            lines.append(f"  {status_icon} {h['step']} — {h['status']}{reason}")

        if state.current_step and pipeline:
            step = pipeline.get_step(state.current_step)
            if step and step.gate:
                lines.append("")
                lines.append(f"门禁要求: 产出 '{step.gate.must_produce}'")
                if step.gate.min_length:
                    lines.append(f"  最小长度: {step.gate.min_length} 字符")

        if state.context:
            lines.append("")
            lines.append(f"上下文键: {', '.join(state.context.keys())}")

        return [types.TextContent(type="text", text="\n".join(lines))]

    # ── pipeline_advance ─────────────────────────────────────────

    def _pipeline_advance(self, args: dict) -> list[types.TextContent]:
        from skills_orchestrator.pipeline.engine import PipelineEngine

        run_id = args.get("run_id", "").strip()
        pipeline_id = args.get("pipeline_id", "").strip()
        context_updates = args.get("context_updates", {}) or {}

        # 读取 artifacts 参数并合并到 context_updates
        artifacts = args.get("artifacts", []) or []
        for artifact in artifacts:
            if not isinstance(artifact, str):
                return [types.TextContent(type="text", text="artifacts 必须是字符串列表")]
            context_updates.setdefault(artifact, True)

        store = self._get_store()
        state = store.load(pipeline_id, run_id)
        if state is None:
            return [types.TextContent(type="text", text=f"找不到运行记录: {pipeline_id}/{run_id}")]

        pipeline = self._get_pipeline(state.pipeline_id)
        if pipeline is None:
            return [types.TextContent(type="text", text=f"Pipeline 不存在: {state.pipeline_id}")]

        engine = PipelineEngine(pipeline)

        # 更新上下文
        state.context.update(context_updates)

        # 使用新的 complete_and_advance 方法（带分支逻辑）
        state = engine.complete_and_advance(state)
        store.save(state)

        # 检查是否失败
        if state.status == "failed":
            lines = [
                "❌ 步骤执行失败",
                f"当前步骤: {state.current_step}",
            ]
            # 从历史记录中获取失败原因
            if state.step_history:
                last_record = state.step_history[-1]
                if last_record.get("status") == "failed":
                    lines.append(f"失败原因: {last_record.get('reason', '未知')}")

            lines.append("")
            lines.append("💡 建议：检查产出是否符合门禁要求，或使用其他 pipeline")
            return [types.TextContent(type="text", text="\n".join(lines))]

        if state.status == "completed":
            return [
                types.TextContent(
                    type="text",
                    text=f"Pipeline '{pipeline.name}' 已完成！\n共 {len(state.step_history)} 个步骤。",
                )
            ]

        next_step = pipeline.get_step(state.current_step) if state.current_step else None
        lines = [
            f"已推进到步骤: {state.current_step} (skill: {next_step.skill if next_step else '?'})",
            f"状态: {state.status}",
        ]
        if next_step and next_step.gate:
            lines.append(f"门禁要求: 产出 '{next_step.gate.must_produce}'")
            if next_step.gate.on_failure:
                lines.append(f"  失败分支: {next_step.gate.on_failure}")
        if next_step and next_step.skip_if:
            lines.append(
                f"跳过条件: {next_step.skip_if} = {state.context.get(next_step.skip_if, False)}"
            )

        # 注入当前步骤的 skill 完整内容到上下文
        if next_step and self._registry is not None:
            skill_content = self._registry.get_content(next_step.skill)
            if skill_content:
                lines.append("")
                lines.append(f"═══ 当前步骤 Skill: {next_step.skill} ═══")
                lines.append(skill_content)
                lines.append("═══════════════════════════════════")

        # 注入门禁要求提示
        if next_step and next_step.gate:
            lines.append("")
            lines.append(f"⚠ 门禁要求: 完成此步骤前必须产出 '{next_step.gate.must_produce}'")
            if next_step.gate.min_length:
                lines.append(f"  最小长度: {next_step.gate.min_length} 字符")
            if next_step.gate.on_failure:
                lines.append(f"  失败时跳转: {next_step.gate.on_failure}")

        lines.append("")
        lines.append(
            f"使用 pipeline_advance(run_id='{run_id}', pipeline_id='{pipeline_id}') 推进下一步。"
        )
        return [types.TextContent(type="text", text="\n".join(lines))]

    # ── pipeline_resume ──────────────────────────────────────────

    def _pipeline_resume(self, args: dict) -> list[types.TextContent]:
        from skills_orchestrator.pipeline.engine import PipelineEngine

        run_id = args.get("run_id", "").strip()
        pipeline_id = args.get("pipeline_id", "").strip()

        store = self._get_store()

        if run_id and pipeline_id:
            state = store.load(pipeline_id, run_id)
        else:
            state = store.load_latest(pipeline_id or None)

        if state is None:
            return [types.TextContent(type="text", text="没有找到可恢复的运行记录。")]

        if state.status == "completed":
            return [
                types.TextContent(
                    type="text", text=f"Pipeline 已完成，无需恢复。Run: {state.run_id}"
                )
            ]

        pipeline = self._get_pipeline(state.pipeline_id)
        if pipeline is None:
            return [types.TextContent(type="text", text=f"Pipeline 不存在: {state.pipeline_id}")]

        engine = PipelineEngine(pipeline)
        state = engine.resume(state)
        store.save(state)

        step = pipeline.get_step(state.current_step) if state.current_step else None
        lines = [
            f"Pipeline '{pipeline.name}' 已恢复！",
            f"Run ID: {state.run_id}",
            f"当前步骤: {state.current_step} (skill: {step.skill if step else '?'})",
            f"状态: {state.status}",
        ]

        # 注入当前步骤的 skill 完整内容到上下文
        if step and self._registry is not None:
            skill_content = self._registry.get_content(step.skill)
            if skill_content:
                lines.append("")
                lines.append(f"═══ 当前步骤 Skill: {step.skill} ═══")
                lines.append(skill_content)
                lines.append("═══════════════════════════════════")

        if step and step.gate:
            lines.append("")
            lines.append(f"⚠ 门禁要求: 完成此步骤前必须产出 '{step.gate.must_produce}'")
            if step.gate.min_length:
                lines.append(f"  最小长度: {step.gate.min_length} 字符")

        lines.append("")
        lines.append(
            f"使用 pipeline_advance(run_id='{state.run_id}', pipeline_id='{state.pipeline_id}') 推进下一步。"
        )
        return [types.TextContent(type="text", text="\n".join(lines))]
