"""Pipeline 状态机引擎 — 驱动步骤流转、跳过、门禁、中断恢复"""

from __future__ import annotations

import uuid
from typing import Optional, Tuple

from .models import Pipeline, RunState, Step


class PipelineEngine:
    """Pipeline 执行引擎"""

    def __init__(self, pipeline: Pipeline):
        self.pipeline = pipeline

    def start(self, context: Optional[dict] = None) -> RunState:
        """启动 Pipeline，返回初始 RunState"""
        run_id = uuid.uuid4().hex[:12]
        state = RunState(
            pipeline_id=self.pipeline.id,
            run_id=run_id,
        )
        if context:
            state.context.update(context)
        if self.pipeline.first_step:
            state.advance_to(self.pipeline.first_step.id)
            # 如果第一步应该被跳过，自动跳过
            state = self._auto_skip(state)
        else:
            state.status = "completed"
        return state

    def advance(self, state: RunState) -> RunState:
        """推进到下一步"""
        current = self._get_current_step(state)

        if current is None:
            if state.status == "running":
                state.status = "completed"
            return state

        # 检查当前步骤是否已完成（step_history 中有记录）
        current_completed = any(
            h["step"] == current.id and h["status"] in ("completed", "skipped", "failed")
            for h in state.step_history
        )

        if not current_completed:
            # 尝试跳过
            if current.skip_if and state.context.get(current.skip_if):
                state.skip_current(reason=current.skip_if)
            else:
                # 当前步骤未完成，无法推进
                return state

        # 找到下一步
        if current.is_terminal:
            state.status = "completed"
            state.current_step = None
            return state

        # 取 next 中的第一个作为下一步（分支逻辑未来扩展）
        next_step_id = current.next[0]
        next_step = self.pipeline.get_step(next_step_id)

        if next_step is None:
            state.fail_current(reason=f"下一步 '{next_step_id}' 不存在")
            return state

        state.advance_to(next_step_id)
        # 自动跳过
        state = self._auto_skip(state)
        return state

    def check_gate(self, state: RunState, step: Step) -> Tuple[bool, str]:
        """检查步骤的门禁条件"""
        if step.gate is None:
            return True, ""
        return step.gate.check(state.context)

    def get_current_step(self, state: RunState) -> Optional[Step]:
        """获取当前步骤的 Step 对象"""
        if state.current_step is None:
            return None
        return self.pipeline.get_step(state.current_step)

    def resume(self, state: RunState) -> RunState:
        """从保存的 RunState 恢复执行"""
        if state.status == "completed":
            return state
        if state.status == "failed":
            # 失败状态：回到当前步骤重试
            state.status = "running"
            return state
        # running 或 paused：继续推进
        return self.advance(state)

    # ── 内部方法 ──────────────────────────────────────

    def _get_current_step(self, state: RunState) -> Optional[Step]:
        """获取当前步骤"""
        if state.current_step is None:
            return None
        return self.pipeline.get_step(state.current_step)

    def _auto_skip(self, state: RunState) -> RunState:
        """自动跳过满足条件的步骤，递归处理连续跳过"""
        current = self._get_current_step(state)
        if current is None:
            return state

        if current.skip_if and state.context.get(current.skip_if):
            state.skip_current(reason=current.skip_if)

            if current.is_terminal:
                state.status = "completed"
                state.current_step = None
                return state

            next_step_id = current.next[0]
            next_step = self.pipeline.get_step(next_step_id)
            if next_step is None:
                state.fail_current(reason=f"下一步 '{next_step_id}' 不存在")
                return state

            state.advance_to(next_step_id)
            return self._auto_skip(state)  # 递归跳过

        return state
