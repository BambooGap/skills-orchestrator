"""Pipeline 数据模型 — Step, Gate, Pipeline, RunState"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple


SENSITIVE_CONTEXT_KEY_RE = re.compile(
    r"(secret|token|password|passwd|credential|authorization|cookie|api[_-]?key|private[_-]?key)",
    re.IGNORECASE,
)
MAX_PERSISTED_STRING_CHARS = 2_000


@dataclass
class Gate:
    """质量门禁：Step 完成前必须满足的条件"""

    must_produce: str | list[str] = ""  # 必须产出的 artifact key(s)
    min_length: int = 0  # artifact 最小字符数
    check_command: str = ""  # 可选：运行命令验证
    max_iterations: int = 0  # 可选：最大重试轮数（0=不限）
    on_failure: Optional[str] = None  # 失败时跳转的步骤 ID

    def required_artifacts(self) -> list[str]:
        """Return normalized artifact keys required by this gate."""
        if not self.must_produce:
            return []
        if isinstance(self.must_produce, str):
            return [self.must_produce]
        if isinstance(self.must_produce, list) and all(
            isinstance(item, str) for item in self.must_produce
        ):
            return [item for item in self.must_produce if item]
        raise TypeError("must_produce 必须是字符串或字符串列表")

    def artifact_label(self) -> str:
        """Human-readable artifact requirement for CLI/MCP output."""
        artifacts = self.required_artifacts()
        if not artifacts:
            return ""
        return ", ".join(artifacts)

    def check(self, context: Dict[str, Any]) -> Tuple[bool, str]:
        """检查门禁是否通过，返回 (passed, reason)"""
        required = self.required_artifacts()
        if not required:
            return True, ""

        for artifact_key in required:
            artifact = context.get(artifact_key)
            if artifact is None:
                return False, f"缺少产出: {artifact_key}"

            if isinstance(artifact, bool) or not isinstance(artifact, (str, bytes, dict)):
                return False, f"产出 '{artifact_key}' 必须是内容、字节或结构化证据"

            if isinstance(artifact, (str, bytes)):
                if not artifact:
                    return False, f"产出 '{artifact_key}' 不能为空"
                if self.min_length > 0 and len(artifact) < self.min_length:
                    return False, (
                        f"产出 '{artifact_key}' 长度 {len(artifact)} < {self.min_length}"
                    )
                continue

            evidence_type = artifact.get("type")
            has_reference = any(
                isinstance(artifact.get(key), str) and artifact[key].strip()
                for key in ("uri", "sha256")
            )
            content = artifact.get("content")
            if (
                not isinstance(evidence_type, str)
                or not evidence_type.strip()
                or not (has_reference or isinstance(content, (str, bytes)))
            ):
                return False, (
                    f"产出 '{artifact_key}' 的结构化证据必须包含 type，且包含 uri、sha256 或 content"
                )
            if self.min_length > 0:
                if not isinstance(content, (str, bytes)):
                    return False, f"产出 '{artifact_key}' 需要可测量的 content 才能使用 min_length"
                if len(content) < self.min_length:
                    return False, (f"产出 '{artifact_key}' 长度 {len(content)} < {self.min_length}")

        return True, ""


@dataclass
class Step:
    """Pipeline 中的一个步骤"""

    id: str  # 步骤唯一 ID
    skill: str  # 引用的 skill ID
    next: List[str] = field(default_factory=list)  # 下一步骤 ID 列表
    skip_if: Optional[str] = None  # 跳过条件（context 中的 bool key）
    gate: Optional[Gate] = None  # 质量门禁
    # 条件分支：gate 失败时跳转的步骤（用于重试或终止）
    on_gate_failure: Optional[str] = None

    @property
    def is_terminal(self) -> bool:
        """是否终止步骤"""
        return len(self.next) == 0

    @property
    def has_branch(self) -> bool:
        """是否有条件分支"""
        return self.on_gate_failure is not None


@dataclass
class Pipeline:
    """可执行的 skill 流水线"""

    id: str
    name: str
    description: str = ""
    steps: List[Step] = field(default_factory=list)

    def __post_init__(self):
        # 构建 step 索引
        self._step_map: Dict[str, Step] = {s.id: s for s in self.steps}

    def get_step(self, step_id: str) -> Optional[Step]:
        """根据 ID 获取 Step"""
        return self._step_map.get(step_id)

    @property
    def first_step(self) -> Optional[Step]:
        """返回第一个 step（列表首元素）"""
        return self.steps[0] if self.steps else None

    def validate(self) -> List[str]:
        """验证 Pipeline 定义完整性，返回错误列表"""
        errors: List[str] = []
        step_ids = set(self._step_map.keys())

        seen_ids: set[str] = set()
        for step in self.steps:
            if step.id in seen_ids:
                errors.append(f"Step id '{step.id}' 重复")
            seen_ids.add(step.id)

        # 检查 next 引用完整性
        for step in self.steps:
            next_ids: List[str] = []
            if not isinstance(step.next, list):
                errors.append(f"Step '{step.id}' 的 next 必须是列表")
            else:
                next_ids = step.next
                if len(next_ids) > 1:
                    errors.append(
                        f"Step '{step.id}' 的 next 最多只能包含一个目标；条件分支尚未实现"
                    )

            for next_id in next_ids:
                if not isinstance(next_id, str):
                    errors.append(f"Step '{step.id}' 的 next 包含非字符串引用")
                    continue
                if next_id not in step_ids:
                    errors.append(f"Step '{step.id}' 的 next='{next_id}' 不存在")

            # 检查 gate.on_failure 引用
            if step.gate and step.gate.on_failure:
                if step.gate.on_failure not in step_ids:
                    errors.append(
                        f"Step '{step.id}' 的 gate.on_failure='{step.gate.on_failure}' 不存在"
                    )

            # 检查 step.on_gate_failure 引用
            if step.on_gate_failure:
                if step.on_gate_failure not in step_ids:
                    errors.append(
                        f"Step '{step.id}' 的 on_gate_failure='{step.on_gate_failure}' 不存在"
                    )

        # Iterative DFS avoids recursion-depth failures for long valid pipelines.
        visited: Set[str] = set()
        path: Set[str] = set()

        for s in self.steps:
            if s.id in visited:
                continue
            stack: list[tuple[str, bool]] = [(s.id, False)]
            while stack:
                sid, exiting = stack.pop()
                if exiting:
                    path.discard(sid)
                    continue
                if sid in path:
                    errors.append(f"检测到循环引用: {sid}")
                    continue
                if sid in visited:
                    continue
                visited.add(sid)
                path.add(sid)
                stack.append((sid, True))
                step = self.get_step(sid)
                if not step:
                    continue
                edges = list(step.next) if isinstance(step.next, list) else []
                if step.gate and step.gate.on_failure:
                    edges.append(step.gate.on_failure)
                if step.on_gate_failure:
                    edges.append(step.on_gate_failure)
                stack.extend((edge, False) for edge in reversed(edges))

        # 可达性检测：Pipeline 从第一个 step 开始执行，未被任何边引用的
        # 后续 step 会被静默跳过，通常是配置错误。
        if self.first_step:
            reachable: Set[str] = set()

            stack = [self.first_step.id]
            while stack:
                sid = stack.pop()
                if sid in reachable or sid not in step_ids:
                    continue
                reachable.add(sid)
                step = self.get_step(sid)
                if not step:
                    continue
                edges = list(step.next) if isinstance(step.next, list) else []
                if step.gate and step.gate.on_failure:
                    edges.append(step.gate.on_failure)
                if step.on_gate_failure:
                    edges.append(step.on_gate_failure)
                stack.extend(reversed(edges))
            for sid in sorted(step_ids - reachable):
                errors.append(f"Step '{sid}' 不可达：未从 first step '{self.first_step.id}' 引用")

        return errors


@dataclass
class RunState:
    """Pipeline 运行时状态（可持久化、可恢复）"""

    pipeline_id: str
    run_id: str
    current_step: Optional[str] = None
    status: str = "pending"  # pending / running / paused / completed / failed
    step_history: List[Dict[str, Any]] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)  # artifact 存储
    started_at: str = ""
    updated_at: str = ""
    revision: int = 0
    _step_start_time: Optional[float] = field(default=None, repr=False, compare=False)

    def __post_init__(self):
        if not self.started_at:
            self.started_at = datetime.now().isoformat()
        if not self.updated_at:
            self.updated_at = datetime.now().isoformat()

    def advance_to(self, step_id: str) -> None:
        """推进到指定步骤"""
        now = datetime.now()
        self.current_step = step_id
        self._step_start_time = now.timestamp()
        self.updated_at = now.isoformat()
        self.status = "running"

    def complete_current(self, artifacts: Optional[List[str]] = None) -> None:
        """完成当前步骤"""
        if self.current_step is None:
            return

        # 计算步骤持续时间
        now = datetime.now()
        duration_s = 0.0
        if self._step_start_time:
            duration_s = round(now.timestamp() - self._step_start_time, 2)

        record: Dict[str, Any] = {
            "step": self.current_step,
            "status": "completed",
            "artifacts": artifacts or [],
            "started_at": self.updated_at,
            "duration_s": duration_s,
        }
        self.step_history.append(record)
        self.updated_at = now.isoformat()

    def skip_current(self, reason: str = "") -> None:
        """跳过当前步骤"""
        if self.current_step is None:
            return

        # 计算步骤持续时间
        now = datetime.now()
        duration_s = 0.0
        if self._step_start_time:
            duration_s = round(now.timestamp() - self._step_start_time, 2)

        record: Dict[str, Any] = {
            "step": self.current_step,
            "status": "skipped",
            "artifacts": [],
            "reason": reason,
            "started_at": self.updated_at,
            "duration_s": duration_s,
        }
        self.step_history.append(record)
        self.updated_at = now.isoformat()

    def fail_current(self, reason: str = "") -> None:
        """标记当前步骤失败"""
        if self.current_step is None:
            return

        # 计算步骤持续时间
        now = datetime.now()
        duration_s = 0.0
        if self._step_start_time:
            duration_s = round(now.timestamp() - self._step_start_time, 2)

        record: Dict[str, Any] = {
            "step": self.current_step,
            "status": "failed",
            "attempt": self.failed_attempts(self.current_step) + 1,
            "artifacts": [],
            "reason": reason,
            "started_at": self.updated_at,
            "duration_s": duration_s,
        }
        self.step_history.append(record)
        self.updated_at = now.isoformat()
        self.status = "failed"

    def failed_attempts(self, step_id: str) -> int:
        """Return the number of failed gate attempts recorded for a step."""
        return sum(
            1
            for record in self.step_history
            if record.get("step") == step_id and record.get("status") == "failed"
        )

    def to_json(self, *, redact_context: bool = True) -> str:
        """序列化为 JSON"""
        context = redact_pipeline_context(self.context) if redact_context else self.context
        return json.dumps(
            {
                "pipeline_id": self.pipeline_id,
                "run_id": self.run_id,
                "current_step": self.current_step,
                "status": self.status,
                "step_history": self.step_history,
                "context": context,
                "started_at": self.started_at,
                "updated_at": self.updated_at,
                "revision": self.revision,
            },
            ensure_ascii=False,
            indent=2,
        )

    @classmethod
    def from_json(cls, json_str: str) -> "RunState":
        """从 JSON 反序列化"""
        data = json.loads(json_str)
        return cls(
            pipeline_id=data["pipeline_id"],
            run_id=data["run_id"],
            current_step=data.get("current_step"),
            status=data.get("status", "pending"),
            step_history=data.get("step_history", []),
            context=data.get("context", {}),
            started_at=data.get("started_at", ""),
            updated_at=data.get("updated_at", ""),
            revision=data.get("revision", 0),
        )


def redact_pipeline_context(value: Any, *, key: str = "") -> Any:
    """Redact sensitive or oversized context values before disk persistence."""
    if key and SENSITIVE_CONTEXT_KEY_RE.search(key):
        return "[REDACTED]"
    if isinstance(value, dict):
        return {str(k): redact_pipeline_context(v, key=str(k)) for k, v in value.items()}
    if isinstance(value, list):
        return [redact_pipeline_context(item) for item in value]
    if isinstance(value, str) and len(value) > MAX_PERSISTED_STRING_CHARS:
        return value[:MAX_PERSISTED_STRING_CHARS] + "\n[TRUNCATED for pipeline state persistence]"
    return value
