"""测试 Pipeline 条件分支功能"""

import sys

from skills_orchestrator.pipeline.loader import PipelineLoader
from skills_orchestrator.pipeline.engine import PipelineEngine


def test_gate_failure_branch():
    """测试 gate 失败时的条件分支"""
    yaml_str = """
id: test-branch
name: 测试分支
steps:
  - id: step1
    skill: skill-a
    next: [step2]
    gate:
      must_produce: result
      on_failure: abort

  - id: step2
    skill: skill-b
    next: []

  - id: abort
    skill: skill-c
    next: []
"""
    loader = PipelineLoader()
    pipeline = loader.load_string(yaml_str)
    engine = PipelineEngine(pipeline)

    # 启动 pipeline
    state = engine.start()
    assert state.current_step == "step1"

    # 没有 result，gate 会失败，应该跳转到 abort
    state = engine.complete_and_advance(state)
    assert state.current_step == "abort", f"期望跳转到 abort，实际是 {state.current_step}"


def test_gate_success_no_branch():
    """测试 gate 成功时不走分支"""
    yaml_str = """
id: test-no-branch
name: 测试正常流程
steps:
  - id: step1
    skill: skill-a
    next: [step2]
    gate:
      must_produce: result
      on_failure: abort

  - id: step2
    skill: skill-b
    next: []

  - id: abort
    skill: skill-c
    next: []
"""
    loader = PipelineLoader()
    pipeline = loader.load_string(yaml_str)
    engine = PipelineEngine(pipeline)

    # 启动 pipeline
    state = engine.start()
    assert state.current_step == "step1"

    # 添加 result，gate 成功，应该走 step2
    state.context["result"] = "success"
    state = engine.complete_and_advance(state)
    assert state.current_step == "step2", f"期望跳转到 step2，实际是 {state.current_step}"


def test_step_on_gate_failure():
    """测试 step 级别的 on_gate_failure"""
    yaml_str = """
id: test-step-branch
name: 测试 step 级别分支
steps:
  - id: step1
    skill: skill-a
    next: [step2]
    on_gate_failure: retry
    gate:
      must_produce: result

  - id: step2
    skill: skill-b
    next: []

  - id: retry
    skill: skill-c
    next: []
"""
    loader = PipelineLoader()
    pipeline = loader.load_string(yaml_str)
    engine = PipelineEngine(pipeline)

    # 启动 pipeline
    state = engine.start()
    assert state.current_step == "step1"

    # 没有 result，gate 失败，应该跳转到 retry
    state = engine.complete_and_advance(state)
    assert state.current_step == "retry", f"期望跳转到 retry，实际是 {state.current_step}"


def test_gate_on_failure_priority():
    """测试 gate.on_failure 优先于 step.on_gate_failure"""
    yaml_str = """
id: test-priority
name: 测试优先级
steps:
  - id: step1
    skill: skill-a
    next: [step2]
    on_gate_failure: retry
    gate:
      must_produce: result
      on_failure: abort

  - id: step2
    skill: skill-b
    next: []

  - id: retry
    skill: skill-c
    next: []

  - id: abort
    skill: skill-d
    next: []
"""
    loader = PipelineLoader()
    pipeline = loader.load_string(yaml_str)
    engine = PipelineEngine(pipeline)

    # 启动 pipeline
    state = engine.start()
    assert state.current_step == "step1"

    # 没有 result，gate 失败
    # gate.on_failure=abort 优先，应该跳转到 abort
    state = engine.complete_and_advance(state)
    assert state.current_step == "abort", f"期望跳转到 abort，实际是 {state.current_step}"


def test_backward_compatibility():
    """测试向后兼容：没有分支字段时正常工作"""
    yaml_str = """
id: test-compat
name: 测试向后兼容
steps:
  - id: step1
    skill: skill-a
    next: [step2]
    gate:
      must_produce: result

  - id: step2
    skill: skill-b
    next: []
"""
    loader = PipelineLoader()
    pipeline = loader.load_string(yaml_str)
    engine = PipelineEngine(pipeline)

    # 启动 pipeline
    state = engine.start()
    assert state.current_step == "step1"

    # 没有 result，gate 失败
    # 没有分支字段，应该标记为失败状态
    state = engine.complete_and_advance(state)
    assert state.status == "failed", f"期望状态为 failed，实际是 {state.status}"
    assert state.current_step == "step1", f"期望停在 step1，实际是 {state.current_step}"

    # 重新开始，添加 result
    state = engine.start()
    state.context["result"] = "success"
    state = engine.complete_and_advance(state)
    assert state.current_step == "step2", f"期望跳转到 step2，实际是 {state.current_step}"


def test_gate_check_command_requires_a_real_successful_verifier():
    pipeline = PipelineLoader().load_string(
        f"""\
id: test-command-gate
name: 测试命令门禁
steps:
  - id: verify
    skill: skill-a
    next: [done]
    gate:
      must_produce: report
      check_command: '{sys.executable} -c "import sys; sys.exit(0)"'
  - id: done
    skill: skill-b
    next: []
"""
    )
    state = PipelineEngine(pipeline).start({"report": "self-reported"})
    state = PipelineEngine(pipeline).complete_and_advance(state)
    assert state.current_step == "done"


def test_gate_check_command_failure_blocks_even_when_artifact_is_reported():
    pipeline = PipelineLoader().load_string(
        f"""\
id: test-command-failure
name: 测试失败命令门禁
steps:
  - id: verify
    skill: skill-a
    next: []
    gate:
      must_produce: report
      check_command: '{sys.executable} -c "import sys; sys.exit(3)"'
"""
    )
    state = PipelineEngine(pipeline).start({"report": "self-reported"})
    state = PipelineEngine(pipeline).complete_and_advance(state)
    assert state.status == "failed"
    assert state.step_history[-1]["reason"] == "检查命令失败（退出码 3）"


def test_gate_check_command_requires_a_string_in_pipeline_yaml():
    try:
        PipelineLoader().load_string(
            """
id: invalid-command-gate
name: 非法命令门禁
steps:
  - id: verify
    skill: skill-a
    next: []
    gate:
      check_command: [python, -m, pytest]
"""
        )
    except ValueError as exc:
        assert "check_command 必须是字符串" in str(exc)
    else:
        raise AssertionError("Expected invalid check_command to be rejected")


def test_gate_max_iterations_prevents_unlimited_resume():
    pipeline = PipelineLoader().load_string(
        """
id: limited-retry
name: limited retry
steps:
  - id: verify
    skill: skill-a
    next: []
    gate:
      must_produce: report
      max_iterations: 1
"""
    )
    engine = PipelineEngine(pipeline)
    state = engine.start()
    state = engine.complete_and_advance(state)
    assert state.status == "failed"
    assert state.failed_attempts("verify") == 1

    resumed = engine.resume(state)
    assert resumed.status == "failed"
    assert resumed.failed_attempts("verify") == 1


if __name__ == "__main__":
    test_gate_failure_branch()
    print("✅ test_gate_failure_branch")

    test_gate_success_no_branch()
    print("✅ test_gate_success_no_branch")

    test_step_on_gate_failure()
    print("✅ test_step_on_gate_failure")

    test_gate_on_failure_priority()
    print("✅ test_gate_on_failure_priority")

    test_backward_compatibility()
    print("✅ test_backward_compatibility")

    print("\n🎉 所有测试通过！")
