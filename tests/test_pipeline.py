"""Pipeline 编排层测试"""

import hashlib
import os
import sys
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import pytest

from skills_orchestrator.pipeline.models import (
    Gate,
    Pipeline,
    RunState,
    Step,
    build_evidence_uri,
)


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

    def test_must_produce_list_requires_all_artifacts(self):
        gate = Gate(must_produce=["root_cause", "test_code"], min_length=5)

        passed, reason = gate.check({"root_cause": "enough"})
        assert not passed
        assert "test_code" in reason

        passed, reason = gate.check({"root_cause": "enough", "test_code": "also enough"})
        assert passed
        assert reason == ""
        assert gate.required_artifacts() == ["root_cause", "test_code"]
        assert gate.artifact_label() == "root_cause, test_code"

    def test_min_length_pass(self):
        gate = Gate(must_produce="plan", min_length=10)
        passed, reason = gate.check({"plan": "A" * 100})
        assert passed

    def test_min_length_fail(self):
        gate = Gate(must_produce="plan", min_length=500)
        passed, reason = gate.check({"plan": "short"})
        assert not passed
        assert "长度" in reason

    def test_artifact_not_string_cannot_bypass_length(self):
        gate = Gate(must_produce="data", min_length=100)
        passed, reason = gate.check({"data": [1, 2, 3]})
        assert not passed
        assert "必须是内容" in reason

    def test_boolean_artifact_cannot_satisfy_gate(self):
        gate = Gate(must_produce="report", min_length=100)
        passed, reason = gate.check({"report": True})
        assert not passed
        assert "必须是内容" in reason

    def test_structured_artifact_requires_evidence_and_measurable_content(self):
        gate = Gate(must_produce="report", min_length=5)
        passed, reason = gate.check({"report": {"type": "file", "uri": "file://report"}})
        assert not passed
        assert "file://" in reason

        passed, reason = gate.check(
            {"report": {"type": "report", "content": "enough", "producer": "ci"}}
        )
        assert passed

    @pytest.mark.parametrize(
        "evidence",
        [
            {"type": "report", "content": ""},
            {"type": "report", "uri": "does-not-exist"},
            {"type": "report", "sha256": "x"},
        ],
    )
    def test_structured_evidence_rejects_empty_or_unverifiable_claims(self, evidence):
        passed, _reason = Gate(must_produce="report").check({"report": evidence})
        assert not passed

    def test_file_evidence_requires_existing_in_root_file_and_matching_hash(self, tmp_path):
        report = tmp_path / "report.txt"
        report.write_text("verified report", encoding="utf-8")
        digest = hashlib.sha256(report.read_bytes()).hexdigest()
        gate = Gate(
            must_produce="report",
            min_length=10,
            require_verified_evidence=True,
            allowed_verifiers=["unit-test"],
        )
        evidence = {
            "type": "report",
            "uri": report.as_uri(),
            "sha256": digest,
            "producer": "ci",
            "verified_by": "unit-test",
            "verified_at": datetime.now(timezone.utc).isoformat(),
        }
        passed, reason = gate.check({"report": evidence}, artifact_root=tmp_path)
        assert passed, reason

        evidence["sha256"] = "0" * 64
        passed, reason = gate.check({"report": evidence}, artifact_root=tmp_path)
        assert not passed
        assert "不匹配" in reason

    def test_verified_evidence_rejects_plain_text_self_claim_and_bad_time(self):
        gate = Gate(
            must_produce="report",
            require_verified_evidence=True,
            allowed_verifiers=["repository-ci"],
            max_evidence_age_seconds=3600,
        )
        passed, reason = gate.check({"report": "done"})
        assert not passed
        assert "结构化证据" in reason

        content = "done"
        evidence = {
            "type": "report",
            "content": content,
            "sha256": hashlib.sha256(content.encode()).hexdigest(),
            "producer": "agent-self-claim",
            "verified_by": "agent-self-claim",
            "verified_at": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
        }
        passed, reason = gate.check({"report": evidence})
        assert not passed
        assert "verifier" in reason

        evidence["verified_by"] = "repository-ci"
        passed, reason = gate.check({"report": evidence})
        assert not passed
        assert "未来" in reason

    def test_verified_inline_evidence_requires_matching_sha256(self):
        gate = Gate(
            must_produce="report",
            require_verified_evidence=True,
            allowed_verifiers=["repository-ci"],
        )
        evidence = {
            "type": "report",
            "content": "done",
            "producer": "ci",
            "verified_by": "repository-ci",
            "verified_at": datetime.now(timezone.utc).isoformat(),
        }
        passed, reason = gate.check({"report": evidence})
        assert not passed
        assert "sha256" in reason

    def test_file_evidence_is_bounded_and_streamed(self, tmp_path, monkeypatch):
        report = tmp_path / "report.bin"
        report.write_bytes(b"x" * 32)
        gate = Gate(must_produce="report", max_artifact_bytes=16)
        evidence = {
            "type": "report",
            "uri": report.as_uri(),
            "sha256": hashlib.sha256(b"x" * 32).hexdigest(),
        }
        monkeypatch.setattr(
            type(report),
            "read_bytes",
            lambda _path: pytest.fail("evidence verification must not call read_bytes"),
        )
        passed, reason = gate.check({"report": evidence}, artifact_root=tmp_path)
        assert not passed
        assert "字节上限" in reason

    def test_file_evidence_rejects_symlinked_parent_directory(self, tmp_path):
        outside = tmp_path.parent / f"{tmp_path.name}-outside"
        outside.mkdir()
        report = outside / "report.txt"
        report.write_text("outside", encoding="utf-8")
        linked = tmp_path / "linked"
        linked.symlink_to(outside, target_is_directory=True)
        evidence = {
            "type": "report",
            "uri": (linked / "report.txt").as_uri(),
            "sha256": hashlib.sha256(b"outside").hexdigest(),
        }

        passed, reason = Gate(must_produce="report").check(
            {"report": evidence}, artifact_root=tmp_path
        )

        assert not passed
        assert "普通文件" in reason

    def test_build_evidence_uri_uses_canonical_root_and_passes_gate(self, tmp_path):
        report = tmp_path / "report.txt"
        report.write_text("canonical", encoding="utf-8")
        uri = build_evidence_uri(report, artifact_root=tmp_path)
        evidence = {
            "type": "report",
            "uri": uri,
            "sha256": hashlib.sha256(b"canonical").hexdigest(),
        }

        passed, reason = Gate(must_produce="report").check(
            {"report": evidence},
            artifact_root=tmp_path.resolve(),
        )

        assert uri == report.resolve().as_uri()
        assert passed, reason

    @pytest.mark.parametrize(
        "suffix",
        [
            "nested/%2e%2e/%2e%2e/outside.txt",
            "nested/%2E%2E/%2E%2E/outside.txt",
            "nested/%252e%252e/outside.txt",
            "nested/%5c..%5coutside.txt",
            "nested/%00outside.txt",
        ],
    )
    def test_file_evidence_encoded_path_corpus_fails_closed(self, tmp_path, suffix):
        (tmp_path / "nested").mkdir()
        evidence = {
            "type": "report",
            "uri": f"{tmp_path.as_uri()}/{suffix}",
            "sha256": "0" * 64,
        }

        passed, _reason = Gate(must_produce="report").check(
            {"report": evidence}, artifact_root=tmp_path
        )

        assert not passed

    @pytest.mark.parametrize("name", ["安全报告.txt", "résumé.txt", "re\u0301sume\u0301.txt"])
    def test_file_evidence_accepts_canonical_unicode_names(self, tmp_path, name):
        report = tmp_path / name
        report.write_text("verified", encoding="utf-8")
        evidence = {
            "type": "report",
            "uri": build_evidence_uri(report, artifact_root=tmp_path),
            "sha256": hashlib.sha256(b"verified").hexdigest(),
        }

        passed, reason = Gate(must_produce="report").check(
            {"report": evidence}, artifact_root=tmp_path
        )

        assert passed, reason


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

    def test_validate_rejects_ambiguous_multi_next(self):
        steps = [
            Step(id="a", skill="s1", next=["b", "c"]),
            Step(id="b", skill="s2", next=["d"]),
            Step(id="c", skill="s3", next=["d"]),
            Step(id="d", skill="s4", next=[]),
        ]
        pipeline = Pipeline(id="diamond", name="菱形", steps=steps)
        errors = pipeline.validate()
        assert any("最多只能包含一个目标" in error for error in errors)

    def test_validate_unreachable_step(self):
        """未被 first step 链路引用的 step 应被标记，避免只执行第一步。"""
        steps = [
            Step(id="a", skill="s1", next=[]),
            Step(id="b", skill="s2", next=[]),
            Step(id="c", skill="s3", next=[]),
        ]
        pipeline = Pipeline(id="unreachable", name="不可达", steps=steps)
        errors = pipeline.validate()
        assert any("Step 'b' 不可达" in e for e in errors)
        assert any("Step 'c' 不可达" in e for e in errors)

    def test_validate_rejects_non_list_next_on_direct_model(self):
        """直接构造模型时 next 类型错误应报清楚。"""
        step = Step(id="a", skill="s1")
        step.next = "b"  # type: ignore[assignment]
        pipeline = Pipeline(id="bad-next", name="坏 next", steps=[step])
        errors = pipeline.validate()
        assert any("next 必须是列表" in e for e in errors)

    def test_validate_rejects_duplicate_step_ids(self):
        pipeline = Pipeline(
            id="duplicates",
            name="重复步骤",
            steps=[Step(id="same", skill="first"), Step(id="same", skill="second")],
        )
        assert any("重复" in error for error in pipeline.validate())


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

    def test_sensitive_context_is_redacted_before_persistence(self):
        state = RunState(pipeline_id="test", run_id="r1")
        state.context["api_token"] = "secret-token"
        state.context["nested"] = {"password": "secret-password"}
        state.context["normal"] = "safe"

        json_str = state.to_json()
        restored = RunState.from_json(json_str)

        assert restored.context["api_token"] == "[REDACTED]"
        assert restored.context["nested"]["password"] == "[REDACTED]"
        assert restored.context["normal"] == "safe"
        assert "secret-token" not in json_str


# ═══════════════════════════════════════════════════════════
# Task 4: PipelineLoader
# ═══════════════════════════════════════════════════════════


class TestPipelineLoader:
    def _pipelines_dir(self):
        return os.path.join(os.path.dirname(__file__), "..", "config", "pipelines")

    def test_load_full_dev(self):
        from skills_orchestrator.pipeline.loader import PipelineLoader

        path = os.path.join(self._pipelines_dir(), "full-dev.yaml")
        loader = PipelineLoader()
        pipeline = loader.load(path)
        assert pipeline.id == "full-dev"
        assert len(pipeline.steps) == 5
        assert pipeline.first_step.id == "brainstorm"

    def test_load_quick_fix(self):
        from skills_orchestrator.pipeline.loader import PipelineLoader

        path = os.path.join(self._pipelines_dir(), "quick-fix.yaml")
        loader = PipelineLoader()
        pipeline = loader.load(path)
        assert pipeline.id == "quick-fix"
        assert len(pipeline.steps) == 3

    def test_load_review_only(self):
        from skills_orchestrator.pipeline.loader import PipelineLoader

        path = os.path.join(self._pipelines_dir(), "review-only.yaml")
        loader = PipelineLoader()
        pipeline = loader.load(path)
        assert pipeline.id == "review-only"
        assert len(pipeline.steps) == 2

    def test_validate_yaml_pipelines(self):
        """所有内置 YAML pipeline 应通过结构验证"""
        from skills_orchestrator.pipeline.loader import PipelineLoader

        loader = PipelineLoader()
        pipelines_dir = self._pipelines_dir()
        for f in os.listdir(pipelines_dir):
            if f.endswith(".yaml"):
                pipeline = loader.load(os.path.join(pipelines_dir, f))
                errors = pipeline.validate()
                assert len(errors) == 0, f"{f} 验证失败: {errors}"

    def test_load_string(self):
        from skills_orchestrator.pipeline.loader import PipelineLoader

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

    def test_load_string_scalar_next_is_normalized(self):
        from skills_orchestrator.pipeline.loader import PipelineLoader

        yaml_str = """
id: test
name: 测试
steps:
  - id: a
    skill: s1
    next: b
  - id: b
    skill: s2
"""
        loader = PipelineLoader()
        pipeline = loader.load_string(yaml_str)
        assert pipeline.get_step("a").next == ["b"]
        assert pipeline.validate() == []

    def test_loader_rejects_duplicate_step_ids_and_multi_next(self):
        from skills_orchestrator.pipeline.loader import PipelineLoader

        with pytest.raises(ValueError, match="重复"):
            PipelineLoader().load_string(
                """
id: duplicate
name: duplicate
steps:
  - id: same
    skill: first
  - id: same
    skill: second
"""
            )
        with pytest.raises(ValueError, match="最多只能包含一个目标"):
            PipelineLoader().load_string(
                """
id: branch
name: branch
steps:
  - id: first
    skill: first
    next: [second, third]
  - id: second
    skill: second
  - id: third
    skill: third
"""
            )

    def test_validate_skills_missing(self):
        from skills_orchestrator.pipeline.loader import PipelineLoader

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
        from skills_orchestrator.pipeline.loader import PipelineLoader

        path = os.path.join(self._pipelines_dir(), "full-dev.yaml")
        loader = PipelineLoader()
        pipeline = loader.load(path)

        plan_step = pipeline.get_step("plan")
        assert plan_step.gate is not None
        assert plan_step.gate.must_produce == "implementation_plan"
        assert plan_step.gate.min_length == 500

    def test_skip_if_parsed(self):
        from skills_orchestrator.pipeline.loader import PipelineLoader

        path = os.path.join(self._pipelines_dir(), "full-dev.yaml")
        loader = PipelineLoader()
        pipeline = loader.load(path)

        brainstorm = pipeline.get_step("brainstorm")
        assert brainstorm.skip_if == "scope_is_trivial"

        plan = pipeline.get_step("plan")
        assert plan.skip_if is None

    def test_production_profile_rejects_self_reported_gate(self):
        from skills_orchestrator.pipeline.loader import PipelineLoader

        with pytest.raises(ValueError, match="Production Step"):
            PipelineLoader().load_string(
                """
id: release
name: Release
profile: production
steps:
  - id: finish
    skill: finish
    gate:
      must_produce: report
"""
            )

    def test_production_profile_requires_complete_verifier_configuration(self):
        from skills_orchestrator.pipeline.loader import PipelineLoader

        pipeline = PipelineLoader().load_string(
            """
id: release
name: Release
profile: production
steps:
  - id: finish
    skill: finish
    gate:
      must_produce: report
      require_verified_evidence: true
      allowed_verifiers: [repository-ci]
      max_evidence_age_seconds: 3600
      max_artifact_bytes: 1024
      check_command: python tools/verify_release.py
"""
        )
        assert pipeline.profile == "production"
        gate = pipeline.first_step.gate
        assert gate is not None
        assert gate.allowed_verifiers == ["repository-ci"]
        assert gate.max_artifact_bytes == 1024


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
        from skills_orchestrator.pipeline.engine import PipelineEngine

        pipeline = self._make_simple_pipeline()
        engine = PipelineEngine(pipeline)
        state = engine.start()
        assert state.current_step == "a"
        assert state.status == "running"

    def test_check_command_receives_stable_execution_id(self, monkeypatch):
        from types import SimpleNamespace

        from skills_orchestrator.pipeline.engine import PipelineEngine

        captured = {}

        def fake_run(_args, **kwargs):
            captured.update(kwargs["env"])
            return SimpleNamespace(returncode=0)

        monkeypatch.setattr("skills_orchestrator.pipeline.engine.subprocess.run", fake_run)
        passed, reason = PipelineEngine._run_check_command(
            "python verifier.py",
            execution_id="execution-123",
            evidence_manifest=[{"artifact": "report", "type": "report", "sha256": "a" * 64}],
        )
        assert passed, reason
        assert captured["SKILLS_ORCHESTRATOR_EXECUTION_ID"] == "execution-123"
        assert '"artifact":"report"' in captured["SKILLS_ORCHESTRATOR_EVIDENCE_MANIFEST"]

    def test_production_engine_direct_call_requires_run_service(self, tmp_path, monkeypatch):
        from skills_orchestrator.pipeline.engine import PipelineEngine

        report = tmp_path / "report.txt"
        report.write_text("verified", encoding="utf-8")
        pipeline = Pipeline(
            id="release",
            name="Release",
            profile="production",
            steps=[
                Step(
                    id="finish",
                    skill="finish",
                    gate=Gate(
                        must_produce="report",
                        check_command="/usr/bin/true",
                        require_verified_evidence=True,
                        allowed_verifiers=["repository-ci"],
                    ),
                )
            ],
        )
        state = PipelineEngine(pipeline, artifact_root=tmp_path).start()
        state.context["report"] = {
            "type": "report",
            "uri": report.as_uri(),
            "sha256": hashlib.sha256(report.read_bytes()).hexdigest(),
            "producer": "ci",
            "verified_by": "repository-ci",
            "verified_at": datetime.now(timezone.utc).isoformat(),
        }
        monkeypatch.setattr(
            "skills_orchestrator.pipeline.engine.subprocess.run",
            lambda *_args, **_kwargs: pytest.fail("verifier must not execute without a lease"),
        )

        state = PipelineEngine(pipeline, artifact_root=tmp_path).complete_and_advance(state)

        assert state.status == "failed"
        assert "PipelineRunService" in state.step_history[-1]["reason"]

    def test_production_verifier_attestation_binds_run_step_and_evidence(self, tmp_path):
        from skills_orchestrator.pipeline.engine import PipelineEngine
        from skills_orchestrator.pipeline.store import RunStateStore

        verifier = tmp_path / "verifier.py"
        verifier.write_text(
            "import json, os\n"
            "keys = ['execution_id', 'pipeline_id', 'run_id', 'step_id', "
            "'evidence_digest', 'verifier']\n"
            "result = {'ok': True}\n"
            "result.update({key: os.environ['SKILLS_ORCHESTRATOR_' + key.upper()] "
            "for key in keys})\n"
            "print(json.dumps(result))\n",
            encoding="utf-8",
        )
        report = tmp_path / "report.txt"
        report.write_text("verified", encoding="utf-8")
        pipeline = Pipeline(
            id="release",
            name="Release",
            profile="production",
            steps=[
                Step(
                    id="finish",
                    skill="finish",
                    gate=Gate(
                        must_produce="report",
                        check_command=f"{sys.executable} {verifier}",
                        require_verified_evidence=True,
                        allowed_verifiers=["repository-ci"],
                    ),
                )
            ],
        )
        engine = PipelineEngine(
            pipeline,
            artifact_root=tmp_path,
            allow_production_execution=True,
        )
        state = engine.start()
        state.context["report"] = {
            "type": "report",
            "uri": report.as_uri(),
            "sha256": hashlib.sha256(report.read_bytes()).hexdigest(),
            "producer": "ci",
            "verified_by": "repository-ci",
            "verified_at": datetime.now(timezone.utc).isoformat(),
        }
        store = RunStateStore(base_dir=str(tmp_path / "state"))
        store.save(state)
        execution_id = store.claim_verification(state, "finish")

        state = engine.complete_and_advance(state, execution_id=execution_id)

        assert state.status == "completed"

    def test_production_true_command_cannot_self_attest(self, tmp_path):
        from skills_orchestrator.pipeline.engine import PipelineEngine
        from skills_orchestrator.pipeline.store import RunStateStore

        report = tmp_path / "report.txt"
        report.write_text("verified", encoding="utf-8")
        pipeline = Pipeline(
            id="release",
            name="Release",
            profile="production",
            steps=[
                Step(
                    id="finish",
                    skill="finish",
                    gate=Gate(
                        must_produce="report",
                        check_command="/usr/bin/true",
                        require_verified_evidence=True,
                        allowed_verifiers=["repository-ci"],
                    ),
                )
            ],
        )
        engine = PipelineEngine(
            pipeline,
            artifact_root=tmp_path,
            allow_production_execution=True,
        )
        state = engine.start()
        state.context["report"] = {
            "type": "report",
            "uri": report.as_uri(),
            "sha256": hashlib.sha256(report.read_bytes()).hexdigest(),
            "producer": "ci",
            "verified_by": "repository-ci",
            "verified_at": datetime.now(timezone.utc).isoformat(),
        }
        store = RunStateStore(base_dir=str(tmp_path / "state"))
        store.save(state)
        execution_id = store.claim_verification(state, "finish")

        state = engine.complete_and_advance(state, execution_id=execution_id)

        assert state.status == "failed"
        assert "JSON attestation" in state.step_history[-1]["reason"]

    def test_production_service_audit_binds_approval_identifiers(self, tmp_path, monkeypatch):
        from skills_orchestrator.mcp.audit import AuditLogger, load_events
        from skills_orchestrator.pipeline.engine import PipelineEngine
        from skills_orchestrator.pipeline.service import PipelineRunService
        from skills_orchestrator.pipeline.store import RunStateStore

        report = tmp_path / "report.txt"
        report.write_text("verified", encoding="utf-8")
        pipeline = Pipeline(
            id="release",
            name="Release",
            profile="production",
            steps=[
                Step(
                    id="finish",
                    skill="finish",
                    gate=Gate(
                        must_produce="report",
                        check_command="repository-verifier",
                        require_verified_evidence=True,
                        allowed_verifiers=["repository-ci"],
                    ),
                )
            ],
        )
        monkeypatch.setattr(
            PipelineEngine,
            "_run_check_command",
            staticmethod(lambda *_args, **_kwargs: (True, "")),
        )
        audit_dir = tmp_path / "audit"
        store = RunStateStore(base_dir=str(tmp_path / "state"))
        service = PipelineRunService(
            pipeline,
            store,
            artifact_root=tmp_path,
            audit=AuditLogger(audit_dir),
        )
        state = service.start()
        evidence = {
            "type": "report",
            "uri": report.as_uri(),
            "sha256": hashlib.sha256(report.read_bytes()).hexdigest(),
            "producer": "ci",
            "verified_by": "repository-ci",
            "verified_at": datetime.now(timezone.utc).isoformat(),
        }

        completed = service.advance(state, context_updates={"report": evidence})
        event = load_events(audit_dir)[-1]
        raw_state = RunState.from_json(
            store._state_path("release", state.run_id).read_text(encoding="utf-8")
        )

        assert completed.status == "completed"
        assert completed.approval_outbox == {}
        assert raw_state.status == "completed"
        assert raw_state.approval_outbox == {}
        assert event["pipeline_id"] == "release"
        assert event["run_id"] == state.run_id
        assert event["step_id"] == "finish"
        assert len(event["execution_id"]) == 32
        assert len(event["evidence_digest"]) == 64
        assert event["verifier"] == "repository-ci"

    def test_production_candidate_state_is_saved_before_gate_passed_audit(
        self, tmp_path, monkeypatch
    ):
        from skills_orchestrator.mcp.audit import AuditLogger, load_events
        from skills_orchestrator.pipeline.engine import PipelineEngine
        from skills_orchestrator.pipeline.service import PipelineRunService
        from skills_orchestrator.pipeline.store import RunStateStore

        report = tmp_path / "report.txt"
        report.write_text("verified", encoding="utf-8")
        pipeline = Pipeline(
            id="release",
            name="Release",
            profile="production",
            steps=[
                Step(
                    id="finish",
                    skill="finish",
                    gate=Gate(
                        must_produce="report",
                        check_command="repository-verifier",
                        require_verified_evidence=True,
                        allowed_verifiers=["repository-ci"],
                    ),
                )
            ],
        )
        monkeypatch.setattr(
            PipelineEngine,
            "_run_check_command",
            staticmethod(lambda *_args, **_kwargs: (True, "")),
        )
        audit_dir = tmp_path / "audit"
        store = RunStateStore(base_dir=str(tmp_path / "state"))
        service = PipelineRunService(
            pipeline,
            store,
            artifact_root=tmp_path,
            audit=AuditLogger(audit_dir),
        )
        state = service.start()
        evidence = {
            "type": "report",
            "uri": report.as_uri(),
            "sha256": hashlib.sha256(report.read_bytes()).hexdigest(),
            "producer": "ci",
            "verified_by": "repository-ci",
            "verified_at": datetime.now(timezone.utc).isoformat(),
        }
        original_save = store.save

        def fail_candidate_save(candidate):
            if candidate.approval_outbox:
                raise OSError("simulated candidate save failure")
            return original_save(candidate)

        monkeypatch.setattr(store, "save", fail_candidate_save)

        with pytest.raises(OSError, match="candidate save failure"):
            service.advance(state, context_updates={"report": evidence})

        persisted = store.load("release", state.run_id)
        events = load_events(audit_dir)
        assert persisted is not None
        assert persisted.status == "verifying"
        assert not any(event.get("outcome") == "gate_passed" for event in events)

    def test_production_outbox_recovers_after_audit_failure(self, tmp_path, monkeypatch):
        from skills_orchestrator.mcp.audit import AuditLogger
        from skills_orchestrator.pipeline.engine import PipelineEngine
        from skills_orchestrator.pipeline.service import PipelineRunService, ProductionAuditError
        from skills_orchestrator.pipeline.store import RunStateStore

        report = tmp_path / "report.txt"
        report.write_text("verified", encoding="utf-8")
        pipeline = Pipeline(
            id="release",
            name="Release",
            profile="production",
            steps=[
                Step(
                    id="finish",
                    skill="finish",
                    gate=Gate(
                        must_produce="report",
                        check_command="repository-verifier",
                        require_verified_evidence=True,
                        allowed_verifiers=["repository-ci"],
                    ),
                )
            ],
        )
        monkeypatch.setattr(
            PipelineEngine,
            "_run_check_command",
            staticmethod(lambda *_args, **_kwargs: (True, "")),
        )
        audit_dir = tmp_path / "audit"
        audit = AuditLogger(audit_dir)
        store = RunStateStore(base_dir=str(tmp_path / "state"))
        service = PipelineRunService(
            pipeline,
            store,
            artifact_root=tmp_path,
            audit=audit,
        )
        state = service.start()
        evidence = {
            "type": "report",
            "uri": report.as_uri(),
            "sha256": hashlib.sha256(report.read_bytes()).hexdigest(),
            "producer": "ci",
            "verified_by": "repository-ci",
            "verified_at": datetime.now(timezone.utc).isoformat(),
        }
        original_append = audit.append

        def fail_step_event(event, *, strict=False):
            if event.get("event") == "pipeline_step_evaluated":
                raise OSError("simulated audit failure")
            return original_append(event, strict=strict)

        monkeypatch.setattr(audit, "append", fail_step_event)
        with pytest.raises(ProductionAuditError, match="audit failure"):
            service.advance(state, context_updates={"report": evidence})

        pending = store.load("release", state.run_id)
        assert pending is not None
        assert pending.status == "pending_audit"
        monkeypatch.setattr(audit, "append", original_append)

        recovered = service.advance(pending)

        assert recovered.status == "completed"
        assert store.load("release", state.run_id).status == "completed"

    def test_production_outbox_rejects_audit_sink_change(self, tmp_path, monkeypatch):
        from skills_orchestrator.mcp.audit import AuditLogger
        from skills_orchestrator.pipeline.engine import PipelineEngine
        from skills_orchestrator.pipeline.service import PipelineRunService, ProductionAuditError
        from skills_orchestrator.pipeline.store import RunStateStore

        report = tmp_path / "report.txt"
        report.write_text("verified", encoding="utf-8")
        pipeline = Pipeline(
            id="release",
            name="Release",
            profile="production",
            steps=[
                Step(
                    id="finish",
                    skill="finish",
                    gate=Gate(
                        must_produce="report",
                        check_command="repository-verifier",
                        require_verified_evidence=True,
                        allowed_verifiers=["repository-ci"],
                    ),
                )
            ],
        )
        monkeypatch.setattr(
            PipelineEngine,
            "_run_check_command",
            staticmethod(lambda *_args, **_kwargs: (True, "")),
        )
        store = RunStateStore(base_dir=str(tmp_path / "state"))
        audit_a = AuditLogger(tmp_path / "audit-a")
        service_a = PipelineRunService(
            pipeline,
            store,
            artifact_root=tmp_path,
            audit=audit_a,
        )
        state = service_a.start()
        evidence = {
            "type": "report",
            "uri": report.as_uri(),
            "sha256": hashlib.sha256(report.read_bytes()).hexdigest(),
            "producer": "ci",
            "verified_by": "repository-ci",
            "verified_at": datetime.now(timezone.utc).isoformat(),
        }
        original_append = audit_a.append

        def fail_step_event(event, *, strict=False):
            if event.get("event") == "pipeline_step_evaluated":
                raise OSError("simulated audit failure")
            return original_append(event, strict=strict)

        monkeypatch.setattr(audit_a, "append", fail_step_event)
        with pytest.raises(ProductionAuditError):
            service_a.advance(state, context_updates={"report": evidence})

        pending = store.load("release", state.run_id)
        assert pending is not None
        service_b = PipelineRunService(
            pipeline,
            store,
            artifact_root=tmp_path,
            audit=AuditLogger(tmp_path / "audit-b"),
        )

        with pytest.raises(ProductionAuditError) as exc_info:
            service_b.advance(pending)

        assert exc_info.value.code == "PRODUCTION_AUDIT_SINK_MISMATCH"
        assert not (tmp_path / "audit-b" / "events.jsonl").exists()

        pending.approval_outbox["event"]["event_id"] = "different-event"
        service_a_recovered = PipelineRunService(
            pipeline,
            store,
            artifact_root=tmp_path,
            audit=AuditLogger(tmp_path / "audit-a"),
        )
        with pytest.raises(ProductionAuditError) as exc_info:
            service_a_recovered.advance(pending)

        assert exc_info.value.code == "PRODUCTION_OUTBOX_INVALID"

    def test_production_outbox_allows_next_step_after_committed_event(self, tmp_path, monkeypatch):
        from skills_orchestrator.mcp.audit import AuditLogger
        from skills_orchestrator.pipeline.engine import PipelineEngine
        from skills_orchestrator.pipeline.service import PipelineRunService
        from skills_orchestrator.pipeline.store import RunStateStore

        report_a = tmp_path / "a.txt"
        report_b = tmp_path / "b.txt"
        report_a.write_text("a", encoding="utf-8")
        report_b.write_text("b", encoding="utf-8")

        def gate(name):
            return Gate(
                must_produce=name,
                check_command="repository-verifier",
                require_verified_evidence=True,
                allowed_verifiers=["repository-ci"],
            )

        pipeline = Pipeline(
            id="release",
            name="Release",
            profile="production",
            steps=[
                Step(id="first", skill="first", next=["second"], gate=gate("report_a")),
                Step(id="second", skill="second", gate=gate("report_b")),
            ],
        )
        monkeypatch.setattr(
            PipelineEngine,
            "_run_check_command",
            staticmethod(lambda *_args, **_kwargs: (True, "")),
        )
        store = RunStateStore(base_dir=str(tmp_path / "state"))
        service = PipelineRunService(
            pipeline,
            store,
            artifact_root=tmp_path,
            audit=AuditLogger(tmp_path / "audit"),
        )
        state = service.start()

        def evidence(path):
            return {
                "type": "report",
                "uri": path.as_uri(),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "producer": "ci",
                "verified_by": "repository-ci",
                "verified_at": datetime.now(timezone.utc).isoformat(),
            }

        state = service.advance(state, context_updates={"report_a": evidence(report_a)})
        state = store.load("release", state.run_id)
        assert state is not None
        assert state.status == "running"
        assert state.current_step == "second"

        state = service.advance(state, context_updates={"report_b": evidence(report_b)})

        assert state.status == "completed"
        assert [record["step"] for record in state.step_history] == ["first", "second"]

    def test_advance_step(self):
        from skills_orchestrator.pipeline.engine import PipelineEngine

        pipeline = self._make_simple_pipeline()
        engine = PipelineEngine(pipeline)
        state = engine.start()
        state.complete_current(artifacts=["artifact_a"])
        state = engine.advance(state)
        assert state.current_step == "b"

    def test_complete_pipeline(self):
        from skills_orchestrator.pipeline.engine import PipelineEngine

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
        from skills_orchestrator.pipeline.engine import PipelineEngine

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
        from skills_orchestrator.pipeline.engine import PipelineEngine

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
        from skills_orchestrator.pipeline.engine import PipelineEngine

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
        from skills_orchestrator.pipeline.engine import PipelineEngine

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

    def test_complete_and_advance_records_multiple_gate_artifacts(self):
        from skills_orchestrator.pipeline.engine import PipelineEngine

        pipeline = Pipeline(
            id="gate-list",
            name="多产物门禁测试",
            steps=[
                Step(
                    id="a",
                    skill="s1",
                    next=[],
                    gate=Gate(must_produce=["root_cause", "test_code"]),
                ),
            ],
        )
        engine = PipelineEngine(pipeline)
        state = engine.start()
        state.context.update({"root_cause": "cause", "test_code": "test"})

        state = engine.complete_and_advance(state)

        assert state.status == "completed"
        assert state.step_history[-1]["artifacts"] == ["root_cause", "test_code"]

    def test_resume_from_saved_state(self):
        """中断恢复：从保存的 RunState 恢复"""
        from skills_orchestrator.pipeline.engine import PipelineEngine

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
        from skills_orchestrator.pipeline.engine import PipelineEngine

        pipeline = self._make_simple_pipeline()
        engine = PipelineEngine(pipeline)
        state = engine.start()
        state.fail_current(reason="test error")
        assert state.status == "failed"

        state = engine.resume(state)
        assert state.status == "running"

    def test_get_current_step(self):
        from skills_orchestrator.pipeline.engine import PipelineEngine

        pipeline = self._make_simple_pipeline()
        engine = PipelineEngine(pipeline)
        state = engine.start()
        step = engine.get_current_step(state)
        assert step is not None
        assert step.id == "a"

    def test_get_current_step_completed(self):
        from skills_orchestrator.pipeline.engine import PipelineEngine

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
        from skills_orchestrator.pipeline.engine import PipelineEngine

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

    def test_deep_consecutive_skips_do_not_recurse(self):
        """极深连续 skip_if 不应触发 Python 递归深度限制。"""
        from skills_orchestrator.pipeline.engine import PipelineEngine

        depth = 1500
        steps = [
            Step(
                id=f"s{i}",
                skill="s",
                next=[f"s{i + 1}"] if i < depth - 1 else [],
                skip_if="skip_all",
            )
            for i in range(depth)
        ]
        pipeline = Pipeline(id="deep-skip", name="深度跳过", steps=steps)
        engine = PipelineEngine(pipeline)

        state = engine.start(context={"skip_all": True})

        assert state.status == "completed"
        assert state.current_step is None
        assert len(state.step_history) == depth


# ═══════════════════════════════════════════════════════════
# Task 6: RunStateStore
# ═══════════════════════════════════════════════════════════


class TestRunStateStore:
    def _make_state(self, pipeline_id="test", run_id="r1"):
        return RunState(pipeline_id=pipeline_id, run_id=run_id)

    def test_save_and_load(self):
        from skills_orchestrator.pipeline.store import RunStateStore

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
            assert loaded.revision == 1

    def test_save_rejects_stale_concurrent_state(self):
        from skills_orchestrator.pipeline.store import ConcurrentStateError, RunStateStore

        with tempfile.TemporaryDirectory() as tmpdir:
            store = RunStateStore(base_dir=tmpdir)
            store.save(self._make_state())
            first = store.load("test", "r1")
            second = store.load("test", "r1")
            assert first is not None and second is not None

            first.context["artifact_a"] = "preserved"
            store.save(first)
            second.context["artifact_b"] = "stale"
            with pytest.raises(ConcurrentStateError, match="revision"):
                store.save(second)

            current = store.load("test", "r1")
            assert current is not None
            assert current.context["artifact_a"] == "preserved"
            assert "artifact_b" not in current.context

    def test_verifier_lease_is_claimed_before_concurrent_execution(self):
        from skills_orchestrator.pipeline.store import (
            ConcurrentStateError,
            RunStateStore,
            VerificationLeaseError,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            store = RunStateStore(base_dir=tmpdir)
            state = self._make_state()
            state.advance_to("verify")
            store.save(state)
            first = store.load("test", "r1")
            stale = store.load("test", "r1")
            assert first is not None and stale is not None

            execution_id = store.claim_verification(first, "verify")
            assert first.status == "verifying"
            assert first.verification["execution_id"] == execution_id

            with pytest.raises(ConcurrentStateError):
                store.claim_verification(stale, "verify")

            current = store.load("test", "r1")
            assert current is not None
            with pytest.raises(VerificationLeaseError):
                store.claim_verification(current, "verify")

    def test_expired_verifier_lease_reuses_execution_id(self):
        from skills_orchestrator.pipeline.store import RunStateStore

        with tempfile.TemporaryDirectory() as tmpdir:
            store = RunStateStore(base_dir=tmpdir)
            state = self._make_state()
            state.advance_to("verify")
            store.save(state)
            original_id = store.claim_verification(state, "verify", lease_seconds=1)
            state.verification["expires_at"] = (
                datetime.now(timezone.utc) - timedelta(seconds=1)
            ).isoformat()
            store.save(state)

            recovered = store.load("test", "r1")
            assert recovered is not None
            recovered_id = store.claim_verification(recovered, "verify")
            assert recovered_id == original_id

    def test_load_nonexistent(self):
        from skills_orchestrator.pipeline.store import RunStateStore

        with tempfile.TemporaryDirectory() as tmpdir:
            store = RunStateStore(base_dir=tmpdir)
            loaded = store.load("no", "such")
            assert loaded is None

    def test_load_latest(self):
        from skills_orchestrator.pipeline.store import RunStateStore

        with tempfile.TemporaryDirectory() as tmpdir:
            store = RunStateStore(base_dir=tmpdir)

            state1 = self._make_state("p1", "r1")
            store.save(state1)

            state2 = self._make_state("p2", "r2")
            store.save(state2)

            latest = store.load_latest()
            assert latest is not None
            assert latest.run_id == "r2"

    def test_load_latest_rejects_tampered_path_escape(self):
        from skills_orchestrator.pipeline.store import RunStateStore

        with tempfile.TemporaryDirectory() as tmpdir:
            store = RunStateStore(base_dir=tmpdir)
            with open(f"{store.runs_dir}/.latest", "w", encoding="utf-8") as f:
                f.write("../outside.json")

            import pytest

            with pytest.raises(ValueError, match="latest"):
                store.load_latest()

    def test_load_latest_by_pipeline(self):
        from skills_orchestrator.pipeline.store import RunStateStore

        with tempfile.TemporaryDirectory() as tmpdir:
            store = RunStateStore(base_dir=tmpdir)

            store.save(self._make_state("p1", "r1"))
            store.save(self._make_state("p2", "r2"))

            latest = store.load_latest(pipeline_id="p1")
            assert latest is not None
            assert latest.pipeline_id == "p1"

    def test_list_runs(self):
        from skills_orchestrator.pipeline.store import RunStateStore

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
        from skills_orchestrator.pipeline.store import RunStateStore

        with tempfile.TemporaryDirectory() as tmpdir:
            store = RunStateStore(base_dir=tmpdir)
            state = self._make_state()
            store.save(state)

            assert store.load("test", "r1") is not None
            deleted = store.delete("test", "r1")
            assert deleted
            assert store.load("test", "r1") is None

    def test_delete_nonexistent(self):
        from skills_orchestrator.pipeline.store import RunStateStore

        with tempfile.TemporaryDirectory() as tmpdir:
            store = RunStateStore(base_dir=tmpdir)
            deleted = store.delete("no", "such")
            assert not deleted

    def test_persistence_across_instances(self):
        """不同 Store 实例应能读取同一份数据"""
        from skills_orchestrator.pipeline.store import RunStateStore

        with tempfile.TemporaryDirectory() as tmpdir:
            store1 = RunStateStore(base_dir=tmpdir)
            state = self._make_state()
            state.context["key"] = "value"
            store1.save(state)

            store2 = RunStateStore(base_dir=tmpdir)
            loaded = store2.load("test", "r1")
            assert loaded is not None
            assert loaded.context["key"] == "value"

    def test_default_store_uses_state_dir_env(self, tmp_path, monkeypatch):
        from skills_orchestrator.pipeline.store import RunStateStore

        state_dir = tmp_path / "project-state"
        monkeypatch.setenv("SKILLS_ORCHESTRATOR_STATE_DIR", str(state_dir))

        store = RunStateStore()
        store.save(self._make_state("p1", "r1"))

        assert store.base_dir == state_dir
        assert (state_dir / "runs" / "p1_r1.json").exists()

    def test_default_store_is_namespaced_under_project_root(self, tmp_path, monkeypatch):
        from skills_orchestrator.pipeline.store import RunStateStore

        monkeypatch.delenv("SKILLS_ORCHESTRATOR_STATE_DIR", raising=False)
        project_a = tmp_path / "project-a"
        project_b = tmp_path / "project-b"
        project_a.mkdir()
        project_b.mkdir()

        store_a = RunStateStore(project_root=project_a)
        store_b = RunStateStore(project_root=project_b)
        store_a.save(self._make_state("p1", "r1"))

        assert store_a.base_dir == project_a / ".skills-orchestrator"
        assert store_b.base_dir == project_b / ".skills-orchestrator"
        assert store_b.load("p1", "r1") is None

    def test_explicit_legacy_state_migration_is_non_destructive(self, tmp_path, monkeypatch):
        from skills_orchestrator.pipeline.store import RunStateStore

        monkeypatch.delenv("SKILLS_ORCHESTRATOR_STATE_DIR", raising=False)
        legacy = RunStateStore(base_dir=str(tmp_path / "legacy"))
        legacy.save(self._make_state("p1", "r1"))
        source_path = legacy.runs_dir / "p1_r1.json"
        original = source_path.read_text(encoding="utf-8")

        target = RunStateStore(project_root=tmp_path / "project")
        first = target.migrate_from(legacy.base_dir)
        second = target.migrate_from(legacy.base_dir)

        assert first == {"copied": 1, "skipped": 0}
        assert second == {"copied": 0, "skipped": 1}
        assert target.load("p1", "r1") is not None
        assert source_path.read_text(encoding="utf-8") == original
        assert (legacy.runs_dir / ".latest").exists()

    def test_legacy_state_migration_rejects_conflicting_target(self, tmp_path, monkeypatch):
        from skills_orchestrator.pipeline.store import RunStateStore

        monkeypatch.delenv("SKILLS_ORCHESTRATOR_STATE_DIR", raising=False)
        legacy = RunStateStore(base_dir=str(tmp_path / "legacy"))
        source_state = self._make_state("p1", "r1")
        source_state.context["origin"] = "legacy"
        legacy.save(source_state)

        target = RunStateStore(project_root=tmp_path / "project")
        target_state = self._make_state("p1", "r1")
        target_state.context["origin"] = "project"
        target.save(target_state)

        with pytest.raises(FileExistsError, match="内容不同"):
            target.migrate_from(legacy.base_dir)

    def test_rejects_path_traversal_identifiers(self):
        """pipeline_id/run_id 不应能通过 ../ 逃逸 runs 目录。"""
        import pytest
        from skills_orchestrator.pipeline.store import RunStateStore

        with tempfile.TemporaryDirectory() as tmpdir:
            store = RunStateStore(base_dir=tmpdir)

            with pytest.raises(ValueError, match="非法"):
                store.save(self._make_state("../evil", "r1"))

            with pytest.raises(ValueError, match="非法"):
                store.load("test", "../../../etc/passwd")

            with pytest.raises(ValueError, match="非法"):
                store.delete("../evil", "r1")


# ═══════════════════════════════════════════════════════════
# Task 7: MCP Pipeline Tools
# ═══════════════════════════════════════════════════════════


class TestPipelineMCPTools:
    """测试 Pipeline MCP 工具的 ToolExecutor 集成"""

    def _make_executor(self, *, max_content_bytes=None):
        from skills_orchestrator.mcp.tools import ToolExecutor
        from skills_orchestrator.mcp.registry import SkillRegistry
        import os

        config_path = os.path.join(os.path.dirname(__file__), "..", "config", "skills.yaml")
        registry = SkillRegistry(config_path)
        pipelines_dir = os.path.join(os.path.dirname(__file__), "..", "config", "pipelines")
        return ToolExecutor(
            registry, pipelines_dir=pipelines_dir, max_content_bytes=max_content_bytes
        )

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

    def test_pipeline_resume_applies_content_byte_limit(self):
        import re

        executor = self._make_executor(max_content_bytes=5)
        result = executor.execute("pipeline_start", {"pipeline_id": "full-dev"})
        text = result[0].text
        assert "TRUNCATED" in text
        run_id = re.search(r"Run ID: (\w+)", text).group(1)

        resumed = executor.execute(
            "pipeline_resume", {"run_id": run_id, "pipeline_id": "full-dev"}
        )[0].text

        assert "TRUNCATED" in resumed

    def test_pipeline_status_no_runs(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            executor = self._make_executor()
            # 用临时目录覆盖 store
            from skills_orchestrator.pipeline.store import RunStateStore

            executor._store = RunStateStore(base_dir=tmpdir)

            result = executor.execute("pipeline_status", {})
            text = result[0].text
            assert "没有找到" in text

    def test_concurrent_advance_runs_verifier_only_after_one_lease(self, tmp_path, monkeypatch):
        import re

        from skills_orchestrator.mcp.registry import SkillRegistry
        from skills_orchestrator.mcp.tools import ToolExecutor
        from skills_orchestrator.pipeline.engine import PipelineEngine
        from skills_orchestrator.pipeline.store import RunStateStore

        pipelines_dir = tmp_path / "pipelines"
        pipelines_dir.mkdir()
        (pipelines_dir / "leased.yaml").write_text(
            """
id: leased
name: Leased verifier
profile: coordination
steps:
  - id: verify
    skill: brainstorming
    gate:
      must_produce: report
      check_command: python verifier.py
""",
            encoding="utf-8",
        )
        config_path = os.path.join(os.path.dirname(__file__), "..", "config", "skills.yaml")
        store = RunStateStore(base_dir=str(tmp_path / "state"))
        executors = [
            ToolExecutor(SkillRegistry(config_path), pipelines_dir=str(pipelines_dir))
            for _ in range(2)
        ]
        for executor in executors:
            executor._store = store

        started = executors[0].execute("pipeline_start", {"pipeline_id": "leased"})
        run_id = re.search(r"Run ID: (\w+)", started[0].text).group(1)

        original_load = store.load
        load_barrier = threading.Barrier(2)

        def synchronized_load(pipeline_id, requested_run_id):
            state = original_load(pipeline_id, requested_run_id)
            if requested_run_id == run_id:
                load_barrier.wait(timeout=5)
            return state

        monkeypatch.setattr(store, "load", synchronized_load)
        verifier_calls = []

        def fake_verifier(
            _command,
            *,
            execution_id=None,
            evidence_manifest=None,
            required_attestation=None,
        ):
            verifier_calls.append(execution_id)
            assert required_attestation is None
            assert evidence_manifest == [
                {
                    "artifact": "report",
                    "type": "inline",
                    "sha256": hashlib.sha256(b"done").hexdigest(),
                }
            ]
            return True, ""

        monkeypatch.setattr(
            PipelineEngine,
            "_run_check_command",
            staticmethod(fake_verifier),
        )
        arguments = {
            "pipeline_id": "leased",
            "run_id": run_id,
            "context_updates": {"report": "done"},
        }
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(
                pool.map(
                    lambda executor: executor.execute("pipeline_advance", arguments),
                    executors,
                )
            )

        assert len(verifier_calls) == 1
        combined = "\n".join(result[0].text for result in results)
        assert "已完成" in combined
        assert "revision" in combined or "verifier" in combined

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
