"""Pipeline 编排层测试"""

import os
import tempfile


from src.pipeline.models import Gate, Pipeline, RunState, Step


# ═══════════════════════════════════════════════════════════
# Task 1: Step + Gate
# ═══════════════════════════════════════════════════════════


class TestGate:
    def test_no_constraint(self):
        gate = Gate()
        passed, reason = gate.check({})
        assert passed
        assert reason == ""

    def test_must_produce_missing(self):
        gate = Gate(must_produce="plan")
        passed, reason = gate.check({})
        assert not passed
        assert "缺少产出" in reason

    def test_must_produce_present(self):
        gate = Gate(must_produce="plan")
        passed, reason = gate.check({"plan": "some content"})
        assert passed

    def test_min_length_pass(self):
        gate = Gate(must_produce="plan", min_length=10)
        passed, reason = gate.check({"plan": "A" * 100})
        assert passed

    def test_min_length_fail(self):
        gate = Gate(must_produce="plan", min_length=500)
        passed, reason = gate.check({"plan": "short"})
        assert not passed
        assert "长度" in reason

    def test_artifact_not_string_ignores_length(self):
        """非字符串 artifact 跳过长度检查"""
        gate = Gate(must_produce="data", min_length=100)
        passed, reason = gate.check({"data": [1, 2, 3]})
        assert passed


class TestStep:
    def test_create_step_minimal(self):
        step = Step(id="brainstorm", skill="brainstorming")
        assert step.id == "brainstorm"
        assert step.skill == "brainstorming"
        assert step.next == []
        assert step.skip_if is None
        assert step.gate is None

    def test_create_step_full(self):
        gate = Gate(must_produce="plan", min_length=500)
        step = Step(
            id="plan",
            skill="writing-plans",
            next=["develop"],
            skip_if=None,
            gate=gate,
        )
        assert step.next == ["develop"]
        assert step.gate.must_produce == "plan"
        assert step.gate.min_length == 500

    def test_step_is_terminal(self):
        step = Step(id="finish", skill="finish-branch", next=[])
        assert step.is_terminal

    def test_step_is_not_terminal(self):
        step = Step(id="plan", skill="writing-plans", next=["develop"])
        assert not step.is_terminal


# ═══════════════════════════════════════════════════════════
# Task 2: Pipeline
# ═══════════════════════════════════════════════════════════


class TestPipeline:
    def test_create_pipeline(self):
        steps = [
            Step(id="a", skill="s1", next=["b"]),
            Step(id="b", skill="s2", next=[]),
        ]
        pipeline = Pipeline(id="test", name="测试", steps=steps)
        assert pipeline.id == "test"
        assert len(pipeline.steps) == 2

    def test_get_step(self):
        steps = [
            Step(id="a", skill="s1", next=["b"]),
            Step(id="b", skill="s2", next=[]),
        ]
        pipeline = Pipeline(id="test", name="测试", steps=steps)
        assert pipeline.get_step("a").skill == "s1"
        assert pipeline.get_step("b").skill == "s2"
        assert pipeline.get_step("c") is None

    def test_first_step(self):
        steps = [
            Step(id="a", skill="s1", next=["b"]),
            Step(id="b", skill="s2", next=[]),
        ]
        pipeline = Pipeline(id="test", name="测试", steps=steps)
        assert pipeline.first_step.id == "a"

    def test_first_step_empty(self):
        pipeline = Pipeline(id="empty", name="空", steps=[])
        assert pipeline.first_step is None

    def test_validate_ok(self):
        steps = [
            Step(id="a", skill="s1", next=["b"]),
            Step(id="b", skill="s2", next=[]),
        ]
        pipeline = Pipeline(id="test", name="测试", steps=steps)
        errors = pipeline.validate()
        assert len(errors) == 0

    def test_validate_no_cycle(self):
        steps = [
            Step(id="a", skill="s1", next=["b"]),
            Step(id="b", skill="s2", next=["a"]),  # 循环
        ]
        pipeline = Pipeline(id="test", name="测试", steps=steps)
        errors = pipeline.validate()
        assert any("循环" in e for e in errors)

    def test_validate_missing_next(self):
        steps = [
            Step(id="a", skill="s1", next=["b"]),  # b 不存在
        ]
        pipeline = Pipeline(id="test", name="测试", steps=steps)
        errors = pipeline.validate()
        assert any("不存在" in e for e in errors)

    def test_validate_diamond_ok(self):
        """菱形依赖（非循环）应该通过"""
        steps = [
            Step(id="a", skill="s1", next=["b", "c"]),
            Step(id="b", skill="s2", next=["d"]),
            Step(id="c", skill="s3", next=["d"]),
            Step(id="d", skill="s4", next=[]),
        ]
        pipeline = Pipeline(id="diamond", name="菱形", steps=steps)
        errors = pipeline.validate()
        assert len(errors) == 0


# ═══════════════════════════════════════════════════════════
# Task 3: RunState
# ═══════════════════════════════════════════════════════════


class TestRunState:
    def test_create_initial_state(self):
        state = RunState(pipeline_id="test", run_id="r1")
        assert state.current_step is None
        assert state.status == "pending"
        assert state.step_history == []

    def test_advance_step(self):
        state = RunState(pipeline_id="test", run_id="r1")
        state.advance_to("brainstorm")
        assert state.current_step == "brainstorm"
        assert state.status == "running"

    def test_complete_step(self):
        state = RunState(pipeline_id="test", run_id="r1")
        state.advance_to("brainstorm")
        state.complete_current(artifacts=["user_intent"])
        assert state.step_history[-1]["step"] == "brainstorm"
        assert state.step_history[-1]["status"] == "completed"
        assert state.step_history[-1]["artifacts"] == ["user_intent"]

    def test_skip_step(self):
        state = RunState(pipeline_id="test", run_id="r1")
        state.advance_to("brainstorm")
        state.skip_current(reason="scope_is_trivial")
        assert state.step_history[-1]["status"] == "skipped"
        assert state.step_history[-1]["reason"] == "scope_is_trivial"

    def test_fail_step(self):
        state = RunState(pipeline_id="test", run_id="r1")
        state.advance_to("brainstorm")
        state.fail_current(reason="timeout")
        assert state.step_history[-1]["status"] == "failed"
        assert state.status == "failed"

    def test_to_json_and_back(self):
        state = RunState(pipeline_id="test", run_id="r1")
        state.advance_to("brainstorm")
        state.complete_current(artifacts=["user_intent"])
        state.advance_to("plan")

        json_str = state.to_json()
        restored = RunState.from_json(json_str)
        assert restored.pipeline_id == "test"
        assert restored.current_step == "plan"
        assert len(restored.step_history) == 1
        assert restored.step_history[0]["artifacts"] == ["user_intent"]

    def test_context_preserved(self):
        state = RunState(pipeline_id="test", run_id="r1")
        state.context["scope_is_trivial"] = True
        state.context["implementation_plan"] = "do stuff"

        json_str = state.to_json()
        restored = RunState.from_json(json_str)
        assert restored.context["scope_is_trivial"] is True
        assert restored.context["implementation_plan"] == "do stuff"


# ═══════════════════════════════════════════════════════════
# Task 4: PipelineLoader
# ═══════════════════════════════════════════════════════════


class TestPipelineLoader:
    def _pipelines_dir(self):
        return os.path.join(os.path.dirname(__file__), "..", "config", "pipelines")

    def test_load_full_dev(self):
        from src.pipeline.loader import PipelineLoader

        path = os.path.join(self._pipelines_dir(), "full-dev.yaml")
        loader = PipelineLoader()
        pipeline = loader.load(path)
        assert pipeline.id == "full-dev"
        assert len(pipeline.steps) == 5
        assert pipeline.first_step.id == "brainstorm"

    def test_load_quick_fix(self):
        from src.pipeline.loader import PipelineLoader

        path = os.path.join(self._pipelines_dir(), "quick-fix.yaml")
        loader = PipelineLoader()
        pipeline = loader.load(path)
        assert pipeline.id == "quick-fix"
        assert len(pipeline.steps) == 3

    def test_load_review_only(self):
        from src.pipeline.loader import PipelineLoader

        path = os.path.join(self._pipelines_dir(), "review-only.yaml")
        loader = PipelineLoader()
        pipeline = loader.load(path)
        assert pipeline.id == "review-only"
        assert len(pipeline.steps) == 2

    def test_validate_yaml_pipelines(self):
        """所有内置 YAML pipeline 应通过结构验证"""
        from src.pipeline.loader import PipelineLoader

        loader = PipelineLoader()
        pipelines_dir = self._pipelines_dir()
        for f in os.listdir(pipelines_dir):
            if f.endswith(".yaml"):
                pipeline = loader.load(os.path.join(pipelines_dir, f))
                errors = pipeline.validate()
                assert len(errors) == 0, f"{f} 验证失败: {errors}"

    def test_load_string(self):
        from src.pipeline.loader import PipelineLoader

        yaml_str = """
id: test
name: 测试
steps:
  - id: a
    skill: s1
    next: [b]
  - id: b
    skill: s2
    next: []
"""
        loader = PipelineLoader()
        pipeline = loader.load_string(yaml_str)
        assert pipeline.id == "test"
        assert len(pipeline.steps) == 2

    def test_validate_skills_missing(self):
        from src.pipeline.loader import PipelineLoader

        path = os.path.join(self._pipelines_dir(), "full-dev.yaml")
        loader = PipelineLoader()
        pipeline = loader.load(path)

        # full-dev 引用: brainstorming, writing-plans, tdd, pr-review, finish-branch
        known_skills = {"brainstorming", "writing-plans", "tdd"}
        missing = loader.validate_skills(pipeline, known_skills)
        assert len(missing) == 2
        assert "pr-review" in missing
        assert "finish-branch" in missing

    def test_gate_parsed_correctly(self):
        from src.pipeline.loader import PipelineLoader

        path = os.path.join(self._pipelines_dir(), "full-dev.yaml")
        loader = PipelineLoader()
        pipeline = loader.load(path)

        plan_step = pipeline.get_step("plan")
        assert plan_step.gate is not None
        assert plan_step.gate.must_produce == "implementation_plan"
        assert plan_step.gate.min_length == 500

    def test_skip_if_parsed(self):
        from src.pipeline.loader import PipelineLoader

        path = os.path.join(self._pipelines_dir(), "full-dev.yaml")
        loader = PipelineLoader()
        pipeline = loader.load(path)

        brainstorm = pipeline.get_step("brainstorm")
        assert brainstorm.skip_if == "scope_is_trivial"

        plan = pipeline.get_step("plan")
        assert plan.skip_if is None


# ═══════════════════════════════════════════════════════════
# Task 5: PipelineEngine
# ═══════════════════════════════════════════════════════════


class TestPipelineEngine:
    def _make_simple_pipeline(self):
        return Pipeline(
            id="simple",
            name="简单流程",
            steps=[
                Step(id="a", skill="s1", next=["b"]),
                Step(id="b", skill="s2", next=[]),
            ],
        )

    def test_start_pipeline(self):
        from src.pipeline.engine import PipelineEngine

        pipeline = self._make_simple_pipeline()
        engine = PipelineEngine(pipeline)
        state = engine.start()
        assert state.current_step == "a"
        assert state.status == "running"

    def test_advance_step(self):
        from src.pipeline.engine import PipelineEngine

        pipeline = self._make_simple_pipeline()
        engine = PipelineEngine(pipeline)
        state = engine.start()
        state.complete_current(artifacts=["artifact_a"])
        state = engine.advance(state)
        assert state.current_step == "b"

    def test_complete_pipeline(self):
        from src.pipeline.engine import PipelineEngine

        pipeline = self._make_simple_pipeline()
        engine = PipelineEngine(pipeline)
        state = engine.start()
        state.complete_current()
        state = engine.advance(state)
        assert state.current_step == "b"
        state.complete_current()
        state = engine.advance(state)
        assert state.status == "completed"
        assert state.current_step is None

    def test_skip_step_on_advance(self):
        from src.pipeline.engine import PipelineEngine

        pipeline = Pipeline(
            id="skip-test",
            name="跳过测试",
            steps=[
                Step(id="a", skill="s1", next=["b"], skip_if="skip_a"),
                Step(id="b", skill="s2", next=[]),
            ],
        )
        engine = PipelineEngine(pipeline)
        state = engine.start()
        state.context["skip_a"] = True
        state = engine.advance(state)
        # a 应被跳过，直接到 b
        assert state.current_step == "b"
        assert state.step_history[-1]["step"] == "a"
        assert state.step_history[-1]["status"] == "skipped"

    def test_auto_skip_on_start(self):
        """启动时如果第一步应跳过，自动跳到第二步"""
        from src.pipeline.engine import PipelineEngine

        pipeline = Pipeline(
            id="auto-skip",
            name="自动跳过测试",
            steps=[
                Step(id="a", skill="s1", next=["b"], skip_if="skip_a"),
                Step(id="b", skill="s2", next=[]),
            ],
        )
        engine = PipelineEngine(pipeline)
        state = engine.start(context={"skip_a": True})
        assert state.current_step == "b"
        assert any(h["step"] == "a" and h["status"] == "skipped" for h in state.step_history)

    def test_gate_check_pass(self):
        from src.pipeline.engine import PipelineEngine

        pipeline = Pipeline(
            id="gate-test",
            name="门禁测试",
            steps=[
                Step(id="a", skill="s1", next=["b"], gate=Gate(must_produce="plan", min_length=10)),
                Step(id="b", skill="s2", next=[]),
            ],
        )
        engine = PipelineEngine(pipeline)
        state = engine.start()
        state.context["plan"] = "A" * 100
        state.complete_current(artifacts=["plan"])
        passed, reason = engine.check_gate(state, pipeline.get_step("a"))
        assert passed

    def test_gate_check_fail(self):
        from src.pipeline.engine import PipelineEngine

        pipeline = Pipeline(
            id="gate-fail",
            name="门禁失败测试",
            steps=[
                Step(
                    id="a", skill="s1", next=["b"], gate=Gate(must_produce="plan", min_length=500)
                ),
                Step(id="b", skill="s2", next=[]),
            ],
        )
        engine = PipelineEngine(pipeline)
        state = engine.start()
        state.context["plan"] = "short"
        state.complete_current(artifacts=["plan"])
        passed, reason = engine.check_gate(state, pipeline.get_step("a"))
        assert not passed

    def test_resume_from_saved_state(self):
        """中断恢复：从保存的 RunState 恢复"""
        from src.pipeline.engine import PipelineEngine

        pipeline = self._make_simple_pipeline()
        engine = PipelineEngine(pipeline)
        state = engine.start()
        state.complete_current()
        json_str = state.to_json()

        # 恢复
        restored = RunState.from_json(json_str)
        engine2 = PipelineEngine(pipeline)
        state2 = engine2.advance(restored)
        assert state2.current_step == "b"

    def test_resume_failed_state(self):
        """恢复失败状态：重置为 running"""
        from src.pipeline.engine import PipelineEngine

        pipeline = self._make_simple_pipeline()
        engine = PipelineEngine(pipeline)
        state = engine.start()
        state.fail_current(reason="test error")
        assert state.status == "failed"

        state = engine.resume(state)
        assert state.status == "running"

    def test_get_current_step(self):
        from src.pipeline.engine import PipelineEngine

        pipeline = self._make_simple_pipeline()
        engine = PipelineEngine(pipeline)
        state = engine.start()
        step = engine.get_current_step(state)
        assert step is not None
        assert step.id == "a"

    def test_get_current_step_completed(self):
        from src.pipeline.engine import PipelineEngine

        pipeline = self._make_simple_pipeline()
        engine = PipelineEngine(pipeline)
        state = engine.start()
        state.complete_current()
        state = engine.advance(state)
        state.complete_current()
        state = engine.advance(state)
        step = engine.get_current_step(state)
        assert step is None

    def test_consecutive_skips(self):
        """连续跳过多个步骤"""
        from src.pipeline.engine import PipelineEngine

        pipeline = Pipeline(
            id="multi-skip",
            name="多步跳过",
            steps=[
                Step(id="a", skill="s1", next=["b"], skip_if="skip_a"),
                Step(id="b", skill="s2", next=["c"], skip_if="skip_b"),
                Step(id="c", skill="s3", next=[]),
            ],
        )
        engine = PipelineEngine(pipeline)
        state = engine.start(context={"skip_a": True, "skip_b": True})
        assert state.current_step == "c"
        assert len(state.step_history) == 2
        assert all(h["status"] == "skipped" for h in state.step_history)


# ═══════════════════════════════════════════════════════════
# Task 6: RunStateStore
# ═══════════════════════════════════════════════════════════


class TestRunStateStore:
    def _make_state(self, pipeline_id="test", run_id="r1"):
        return RunState(pipeline_id=pipeline_id, run_id=run_id)

    def test_save_and_load(self):
        from src.pipeline.store import RunStateStore

        with tempfile.TemporaryDirectory() as tmpdir:
            store = RunStateStore(base_dir=tmpdir)
            state = self._make_state()
            state.advance_to("step_a")

            filepath = store.save(state)
            assert filepath.exists()

            loaded = store.load("test", "r1")
            assert loaded is not None
            assert loaded.run_id == "r1"
            assert loaded.current_step == "step_a"

    def test_load_nonexistent(self):
        from src.pipeline.store import RunStateStore

        with tempfile.TemporaryDirectory() as tmpdir:
            store = RunStateStore(base_dir=tmpdir)
            loaded = store.load("no", "such")
            assert loaded is None

    def test_load_latest(self):
        from src.pipeline.store import RunStateStore

        with tempfile.TemporaryDirectory() as tmpdir:
            store = RunStateStore(base_dir=tmpdir)

            state1 = self._make_state("p1", "r1")
            store.save(state1)

            state2 = self._make_state("p2", "r2")
            store.save(state2)

            latest = store.load_latest()
            assert latest is not None
            assert latest.run_id == "r2"

    def test_load_latest_by_pipeline(self):
        from src.pipeline.store import RunStateStore

        with tempfile.TemporaryDirectory() as tmpdir:
            store = RunStateStore(base_dir=tmpdir)

            store.save(self._make_state("p1", "r1"))
            store.save(self._make_state("p2", "r2"))

            latest = store.load_latest(pipeline_id="p1")
            assert latest is not None
            assert latest.pipeline_id == "p1"

    def test_list_runs(self):
        from src.pipeline.store import RunStateStore

        with tempfile.TemporaryDirectory() as tmpdir:
            store = RunStateStore(base_dir=tmpdir)

            store.save(self._make_state("p1", "r1"))
            store.save(self._make_state("p1", "r2"))
            store.save(self._make_state("p2", "r3"))

            runs = store.list_runs()
            assert len(runs) == 3

            p1_runs = store.list_runs(pipeline_id="p1")
            assert len(p1_runs) == 2

    def test_delete(self):
        from src.pipeline.store import RunStateStore

        with tempfile.TemporaryDirectory() as tmpdir:
            store = RunStateStore(base_dir=tmpdir)
            state = self._make_state()
            store.save(state)

            assert store.load("test", "r1") is not None
            deleted = store.delete("test", "r1")
            assert deleted
            assert store.load("test", "r1") is None

    def test_delete_nonexistent(self):
        from src.pipeline.store import RunStateStore

        with tempfile.TemporaryDirectory() as tmpdir:
            store = RunStateStore(base_dir=tmpdir)
            deleted = store.delete("no", "such")
            assert not deleted

    def test_persistence_across_instances(self):
        """不同 Store 实例应能读取同一份数据"""
        from src.pipeline.store import RunStateStore

        with tempfile.TemporaryDirectory() as tmpdir:
            store1 = RunStateStore(base_dir=tmpdir)
            state = self._make_state()
            state.context["key"] = "value"
            store1.save(state)

            store2 = RunStateStore(base_dir=tmpdir)
            loaded = store2.load("test", "r1")
            assert loaded is not None
            assert loaded.context["key"] == "value"


# ═══════════════════════════════════════════════════════════
# Task 7: MCP Pipeline Tools
# ═══════════════════════════════════════════════════════════


class TestPipelineMCPTools:
    """测试 Pipeline MCP 工具的 ToolExecutor 集成"""

    def _make_executor(self):
        from src.mcp.tools import ToolExecutor
        from src.mcp.registry import SkillRegistry
        import os

        config_path = os.path.join(os.path.dirname(__file__), "..", "config", "skills.yaml")
        registry = SkillRegistry(config_path)
        pipelines_dir = os.path.join(os.path.dirname(__file__), "..", "config", "pipelines")
        return ToolExecutor(registry, pipelines_dir=pipelines_dir)

    def test_pipeline_start_full_dev(self):
        executor = self._make_executor()
        result = executor.execute("pipeline_start", {"pipeline_id": "full-dev"})
        text = result[0].text
        assert "已启动" in text
        assert "full-dev" in text
        assert "Run ID:" in text
        assert "brainstorm" in text

    def test_pipeline_start_with_skip_context(self):
        executor = self._make_executor()
        result = executor.execute(
            "pipeline_start",
            {
                "pipeline_id": "full-dev",
                "context": {"scope_is_trivial": True},
            },
        )
        text = result[0].text
        assert "plan" in text  # brainstorm 被跳过，直接到 plan

    def test_pipeline_start_nonexistent(self):
        executor = self._make_executor()
        result = executor.execute("pipeline_start", {"pipeline_id": "nonexistent"})
        text = result[0].text
        assert "找不到" in text

    def test_pipeline_start_no_id_lists_available(self):
        executor = self._make_executor()
        result = executor.execute("pipeline_start", {})
        text = result[0].text
        assert "请提供" in text

    def test_pipeline_status_after_start(self):
        import re

        executor = self._make_executor()
        result = executor.execute("pipeline_start", {"pipeline_id": "full-dev"})
        text = result[0].text
        # 提取 run_id
        match = re.search(r"Run ID: (\w+)", text)
        assert match
        run_id = match.group(1)

        result2 = executor.execute("pipeline_status", {"run_id": run_id, "pipeline_id": "full-dev"})
        text2 = result2[0].text
        assert "full-dev" in text2
        assert run_id in text2

    def test_pipeline_status_no_runs(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            executor = self._make_executor()
            # 用临时目录覆盖 store
            from src.pipeline.store import RunStateStore

            executor._store = RunStateStore(base_dir=tmpdir)

            result = executor.execute("pipeline_status", {})
            text = result[0].text
            assert "没有找到" in text

    def test_full_dev_pipeline_walkthrough(self):
        """完整走一遍 full-dev pipeline：启动→逐步推进→完成"""
        import re

        executor = self._make_executor()

        # 启动
        result = executor.execute("pipeline_start", {"pipeline_id": "full-dev"})
        text = result[0].text
        match = re.search(r"Run ID: (\w+)", text)
        run_id = match.group(1)

        # 推进 brainstorm → plan (门禁: brainstorm_output)
        result = executor.execute(
            "pipeline_advance",
            {
                "run_id": run_id,
                "pipeline_id": "full-dev",
                "artifacts": ["brainstorm_output"],
                "context_updates": {"brainstorm_output": "功能构想和关键决策"},
            },
        )
        assert "plan" in result[0].text

        # 推进 plan → develop (门禁: implementation_plan, min_length 500)
        result = executor.execute(
            "pipeline_advance",
            {
                "run_id": run_id,
                "pipeline_id": "full-dev",
                "artifacts": ["implementation_plan"],
                "context_updates": {"implementation_plan": "A" * 600},
            },
        )
        text = result[0].text
        assert "develop" in text or "review" in text or "已完成" in text

        # 推进 develop → review (门禁: code_changes)
        result = executor.execute(
            "pipeline_advance",
            {
                "run_id": run_id,
                "pipeline_id": "full-dev",
                "artifacts": ["code_changes"],
                "context_updates": {"code_changes": "changed files"},
            },
        )

        # 推进 review → finish (门禁: review_feedback)
        result = executor.execute(
            "pipeline_advance",
            {
                "run_id": run_id,
                "pipeline_id": "full-dev",
                "artifacts": ["review_feedback"],
                "context_updates": {"review_feedback": "LGTM"},
            },
        )

        # 推进 finish → 完成 (门禁: merge_confirmation)
        result = executor.execute(
            "pipeline_advance",
            {
                "run_id": run_id,
                "pipeline_id": "full-dev",
                "artifacts": ["merge_confirmation"],
                "context_updates": {"merge_confirmation": "merged"},
            },
        )

        text = result[0].text
        assert "已完成" in text or "completed" in text.lower() or "5 个步骤" in text
