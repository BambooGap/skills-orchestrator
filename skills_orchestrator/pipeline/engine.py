"""Pipeline 状态机引擎 — 驱动步骤流转、跳过、门禁、中断恢复"""

from __future__ import annotations

import hashlib
import json
import shlex
import subprocess
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Tuple

from skills_orchestrator.security import safe_subprocess_env, subprocess_text_kwargs

from .models import Pipeline, RunState, Step


CHECK_COMMAND_TIMEOUT_SECONDS = 60
MAX_VERIFIER_OUTPUT_BYTES = 64 * 1024


class PipelineEngine:
    """Pipeline 执行引擎"""

    def __init__(
        self,
        pipeline: Pipeline,
        *,
        artifact_root: str | Path | None = None,
        allow_production_execution: bool = False,
    ):
        errors = pipeline.validate()
        if errors:
            raise ValueError("Pipeline 定义无效: " + "; ".join(errors))
        self.pipeline = pipeline
        self.artifact_root = Path(artifact_root or Path.cwd()).resolve()
        self._allow_production_execution = allow_production_execution

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
        """推进到下一步（假设 gate 已通过）"""
        if self.pipeline.profile == "production":
            raise RuntimeError("Production Pipeline 必须通过 PipelineRunService 推进")
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

        # 默认行为：走 next[0]
        next_step_id = current.next[0] if current.next else ""
        next_step = self.pipeline.get_step(next_step_id)

        if next_step is None:
            state.fail_current(reason=f"下一步 '{next_step_id}' 不存在")
            return state

        state.advance_to(next_step_id)
        # 自动跳过
        state = self._auto_skip(state)
        return state

    def complete_and_advance(self, state: RunState, *, execution_id: str | None = None) -> RunState:
        """完成当前步骤并推进到下一步（带 gate 检查和分支逻辑）

        这是推荐使用的推进方法，会：
        1. 检查 gate 是否通过
        2. 根据结果标记步骤状态（completed/failed）
        3. 根据分支配置决定下一步
        """
        current = self._get_current_step(state)

        if current is None:
            if state.status == "running":
                state.status = "completed"
            return state
        if self.pipeline.profile == "production" and not self._allow_production_execution:
            state.fail_current(reason="Production Pipeline 必须通过 PipelineRunService 推进")
            return state

        # 检查 gate
        gate_passed = True
        gate_reason = ""
        if current.gate:
            if (
                current.gate.max_iterations > 0
                and state.failed_attempts(current.id) >= current.gate.max_iterations
            ):
                state.fail_current(
                    reason=(
                        f"步骤 '{current.id}' 已达到 max_iterations="
                        f"{current.gate.max_iterations}，拒绝继续自动恢复"
                    )
                )
                return state
            gate_passed, gate_reason = current.gate.check(
                state.context, artifact_root=self.artifact_root
            )
            if gate_passed and current.gate.check_command:
                binding: dict[str, str] | None = None
                if self.pipeline.profile == "production":
                    binding, gate_reason = self._production_verifier_binding(
                        state, current, execution_id
                    )
                    if binding is None:
                        gate_passed = False
                if gate_passed:
                    gate_passed, gate_reason = self._run_check_command(
                        current.gate.check_command,
                        execution_id=execution_id,
                        evidence_manifest=self._evidence_manifest(current.gate, state.context),
                        required_attestation=binding,
                    )

        if not gate_passed:
            # Gate 失败
            state.fail_current(reason=gate_reason)

            # 检查是否有失败分支
            next_step_id = None
            if current.gate and current.gate.on_failure:
                next_step_id = current.gate.on_failure
            elif current.on_gate_failure:
                next_step_id = current.on_gate_failure

            if next_step_id:
                # 跳转到失败分支
                next_step = self.pipeline.get_step(next_step_id)
                if next_step:
                    state.status = "running"  # 重置状态
                    state.advance_to(next_step_id)
                    return self._auto_skip(state)

            # 没有失败分支，停在失败状态
            return state

        # Gate 通过，标记完成
        artifacts = []
        if current.gate and current.gate.must_produce:
            artifacts = current.gate.required_artifacts()
        state.complete_current(artifacts=artifacts)

        # 找到下一步
        if current.is_terminal:
            state.status = "completed"
            state.current_step = None
            return state

        next_step_id = current.next[0] if current.next else ""
        next_step = self.pipeline.get_step(next_step_id)

        if next_step is None:
            state.fail_current(reason=f"下一步 '{next_step_id}' 不存在")
            return state

        state.advance_to(next_step_id)
        return self._auto_skip(state)

    def check_gate(self, state: RunState, step: Step) -> Tuple[bool, str]:
        """检查步骤的门禁条件"""
        if step.gate is None:
            return True, ""
        passed, reason = step.gate.check(state.context, artifact_root=self.artifact_root)
        if passed and step.gate.check_command:
            if self.pipeline.profile == "production":
                return False, "Production Pipeline 必须通过 PipelineRunService 验证"
            return self._run_check_command(
                step.gate.check_command,
                evidence_manifest=self._evidence_manifest(step.gate, state.context),
            )
        return passed, reason

    @staticmethod
    def _run_check_command(
        command: str,
        *,
        execution_id: str | None = None,
        evidence_manifest: list[dict[str, str]] | None = None,
        required_attestation: dict[str, str] | None = None,
    ) -> Tuple[bool, str]:
        """Run a trusted-pipeline verifier without a shell or inherited secrets."""
        try:
            args = shlex.split(command)
        except ValueError as exc:
            return False, f"检查命令格式无效: {exc}"
        if not args:
            return False, "检查命令不能为空"

        output = b""
        try:
            env = safe_subprocess_env()
            if execution_id:
                env["SKILLS_ORCHESTRATOR_EXECUTION_ID"] = execution_id
            if evidence_manifest is not None:
                env["SKILLS_ORCHESTRATOR_EVIDENCE_MANIFEST"] = json.dumps(
                    evidence_manifest,
                    ensure_ascii=True,
                    separators=(",", ":"),
                )
            if required_attestation is not None:
                for key, value in required_attestation.items():
                    env[f"SKILLS_ORCHESTRATOR_{key.upper()}"] = value
                with tempfile.TemporaryFile() as stdout:
                    result = subprocess.run(
                        args,
                        stdin=subprocess.DEVNULL,
                        stdout=stdout,
                        stderr=subprocess.DEVNULL,
                        env=env,
                        timeout=CHECK_COMMAND_TIMEOUT_SECONDS,
                        check=False,
                    )
                    size = stdout.tell()
                    if size > MAX_VERIFIER_OUTPUT_BYTES:
                        return False, (
                            f"生产 verifier 输出超过 {MAX_VERIFIER_OUTPUT_BYTES} 字节上限"
                        )
                    stdout.seek(0)
                    output = stdout.read(MAX_VERIFIER_OUTPUT_BYTES + 1)
            else:
                result = subprocess.run(
                    args,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    env=env,
                    timeout=CHECK_COMMAND_TIMEOUT_SECONDS,
                    check=False,
                    **subprocess_text_kwargs(),
                )
        except FileNotFoundError:
            return False, f"检查命令不存在: {args[0]}"
        except PermissionError:
            return False, f"检查命令无执行权限: {args[0]}"
        except subprocess.TimeoutExpired:
            return False, f"检查命令超时（>{CHECK_COMMAND_TIMEOUT_SECONDS} 秒）"

        if result.returncode != 0:
            return False, f"检查命令失败（退出码 {result.returncode}）"
        if required_attestation is not None:
            try:
                attestation = json.loads(output.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                return False, "生产 verifier 必须输出单个 UTF-8 JSON attestation"
            if not isinstance(attestation, dict) or attestation.get("ok") is not True:
                return False, "生产 verifier attestation 必须包含 ok=true"
            for key, expected in required_attestation.items():
                if attestation.get(key) != expected:
                    return False, f"生产 verifier attestation 的 {key} 与当前执行不匹配"
        return True, ""

    def _production_verifier_binding(
        self,
        state: RunState,
        step: Step,
        execution_id: str | None,
    ) -> tuple[dict[str, str] | None, str]:
        """Bind a production verifier result to its exact lease and evidence set."""
        if not execution_id:
            return None, "Production verifier 缺少 execution_id 和已持久化租约"
        lease = state.verification
        if (
            lease.get("execution_id") != execution_id
            or lease.get("step_id") != step.id
            or state.status != "verifying"
        ):
            return None, "Production verifier 的 execution_id 与当前租约不匹配"
        try:
            expires_at = datetime.fromisoformat(
                str(lease.get("expires_at") or "").replace("Z", "+00:00")
            )
        except ValueError:
            return None, "Production verifier 租约缺少有效过期时间"
        if expires_at.tzinfo is None or expires_at <= datetime.now(timezone.utc):
            return None, "Production verifier 租约已过期"

        gate = step.gate
        if gate is None:
            return None, "Production Step 缺少 gate"
        missing = [key for key in gate.required_artifacts() if key not in state.context]
        if missing:
            return None, f"Production verifier 缺少 evidence: {', '.join(missing)}"
        manifest = self._evidence_manifest(gate, state.context)
        if not manifest or any(not entry.get("uri") for entry in manifest):
            return None, "Production verifier 只接受 file:// evidence，不接受 inline content"
        verifiers = {entry.get("verified_by", "") for entry in manifest}
        if len(verifiers) != 1 or "" in verifiers:
            return None, "Production evidence 必须绑定同一个 verifier 身份"
        encoded = json.dumps(
            manifest,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return (
            {
                "execution_id": execution_id,
                "pipeline_id": state.pipeline_id,
                "run_id": state.run_id,
                "step_id": step.id,
                "evidence_digest": hashlib.sha256(encoded).hexdigest(),
                "verifier": next(iter(verifiers)),
            },
            "",
        )

    @staticmethod
    def _evidence_manifest(gate, context: dict) -> list[dict[str, str]]:
        """Describe the exact evidence set to the repository-controlled verifier."""
        manifest = []
        for key in gate.required_artifacts():
            evidence = context[key]
            if isinstance(evidence, dict):
                entry = {
                    "artifact": key,
                    "type": str(evidence.get("type") or ""),
                    "sha256": str(evidence.get("sha256") or ""),
                }
                if evidence.get("uri"):
                    entry["uri"] = str(evidence["uri"])
                if evidence.get("verified_by"):
                    entry["verified_by"] = str(evidence["verified_by"])
            else:
                raw = evidence.encode("utf-8") if isinstance(evidence, str) else evidence
                entry = {
                    "artifact": key,
                    "type": "inline",
                    "sha256": hashlib.sha256(raw).hexdigest(),
                }
            manifest.append(entry)
        return manifest

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
            current = self._get_current_step(state)
            if (
                current
                and current.gate
                and current.gate.max_iterations > 0
                and state.failed_attempts(current.id) >= current.gate.max_iterations
            ):
                return state
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
        """自动跳过满足条件的连续步骤。"""
        while True:
            current = self._get_current_step(state)
            if current is None:
                return state

            if not (current.skip_if and state.context.get(current.skip_if)):
                return state

            state.skip_current(reason=current.skip_if)

            if current.is_terminal or not current.next:
                state.status = "completed"
                state.current_step = None
                return state

            next_step_id = current.next[0]
            next_step = self.pipeline.get_step(next_step_id)
            if next_step is None:
                state.fail_current(reason=f"下一步 '{next_step_id}' 不存在")
                return state

            state.advance_to(next_step_id)
