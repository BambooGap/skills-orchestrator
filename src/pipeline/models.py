"""Pipeline 数据模型 — Step, Gate, Pipeline, RunState"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple


@dataclass
class Gate:
    """质量门禁：Step 完成前必须满足的条件"""

    must_produce: str = ""              # 必须产出的 artifact key
    min_length: int = 0                 # artifact 最小字符数
    check_command: str = ""             # 可选：运行命令验证
    max_iterations: int = 0             # 可选：最大重试轮数（0=不限）

    def check(self, context: Dict[str, Any]) -> Tuple[bool, str]:
        """检查门禁是否通过，返回 (passed, reason)"""
        if not self.must_produce:
            return True, ""

        artifact = context.get(self.must_produce)
        if artifact is None:
            return False, f"缺少产出: {self.must_produce}"

        if isinstance(artifact, str) and self.min_length > 0:
            if len(artifact) < self.min_length:
                return False, (
                    f"产出 '{self.must_produce}' 长度 {len(artifact)} < {self.min_length}"
                )

        return True, ""


@dataclass
class Step:
    """Pipeline 中的一个步骤"""

    id: str                              # 步骤唯一 ID
    skill: str                           # 引用的 skill ID
    next: List[str] = field(default_factory=list)  # 下一步骤 ID 列表
    skip_if: Optional[str] = None        # 跳过条件（context 中的 bool key）
    gate: Optional[Gate] = None          # 质量门禁

    @property
    def is_terminal(self) -> bool:
        """是否终止步骤"""
        return len(self.next) == 0


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

        # 检查 next 引用完整性
        for step in self.steps:
            for next_id in step.next:
                if next_id not in step_ids:
                    errors.append(f"Step '{step.id}' 的 next='{next_id}' 不存在")

        # 简单循环检测：DFS
        visited: Set[str] = set()
        path: Set[str] = set()

        def _dfs(sid: str) -> None:
            if sid in path:
                errors.append(f"检测到循环引用: {sid}")
                return
            if sid in visited:
                return
            visited.add(sid)
            path.add(sid)
            step = self.get_step(sid)
            if step:
                for nid in step.next:
                    _dfs(nid)
            path.discard(sid)

        for s in self.steps:
            _dfs(s.id)

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

    def __post_init__(self):
        if not self.started_at:
            self.started_at = datetime.now().isoformat()
        self.updated_at = datetime.now().isoformat()

    def advance_to(self, step_id: str) -> None:
        """推进到指定步骤"""
        self.current_step = step_id
        self.status = "running"
        self.updated_at = datetime.now().isoformat()

    def complete_current(self, artifacts: Optional[List[str]] = None) -> None:
        """完成当前步骤"""
        if self.current_step is None:
            return
        record: Dict[str, Any] = {
            "step": self.current_step,
            "status": "completed",
            "artifacts": artifacts or [],
            "started_at": self.updated_at,
            "duration_s": 0,
        }
        self.step_history.append(record)
        self.updated_at = datetime.now().isoformat()

    def skip_current(self, reason: str = "") -> None:
        """跳过当前步骤"""
        if self.current_step is None:
            return
        record: Dict[str, Any] = {
            "step": self.current_step,
            "status": "skipped",
            "artifacts": [],
            "reason": reason,
            "started_at": self.updated_at,
            "duration_s": 0,
        }
        self.step_history.append(record)
        self.updated_at = datetime.now().isoformat()

    def fail_current(self, reason: str = "") -> None:
        """标记当前步骤失败"""
        if self.current_step is None:
            return
        record: Dict[str, Any] = {
            "step": self.current_step,
            "status": "failed",
            "artifacts": [],
            "reason": reason,
            "started_at": self.updated_at,
            "duration_s": 0,
        }
        self.step_history.append(record)
        self.status = "failed"
        self.updated_at = datetime.now().isoformat()

    def to_json(self) -> str:
        """序列化为 JSON"""
        return json.dumps({
            "pipeline_id": self.pipeline_id,
            "run_id": self.run_id,
            "current_step": self.current_step,
            "status": self.status,
            "step_history": self.step_history,
            "context": self.context,
            "started_at": self.started_at,
            "updated_at": self.updated_at,
        }, ensure_ascii=False, indent=2)

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
        )
