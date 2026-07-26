"""Pipeline 数据模型 — Step, Gate, Pipeline, RunState"""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import unquote, urlparse


SENSITIVE_CONTEXT_KEY_RE = re.compile(
    r"(secret|token|password|passwd|credential|authorization|cookie|api[_-]?key|private[_-]?key)",
    re.IGNORECASE,
)
MAX_PERSISTED_STRING_CHARS = 2_000
SHA256_RE = re.compile(r"^[0-9a-f]{64}$", re.IGNORECASE)
DEFAULT_MAX_ARTIFACT_BYTES = 20 * 1024 * 1024
DEFAULT_MAX_EVIDENCE_AGE_SECONDS = 24 * 60 * 60
MAX_EVIDENCE_FUTURE_SKEW_SECONDS = 5 * 60
HASH_CHUNK_BYTES = 1024 * 1024


def build_evidence_uri(
    path: str | os.PathLike[str],
    *,
    artifact_root: str | os.PathLike[str],
) -> str:
    """Return a canonical file URI that is safely contained by artifact_root."""
    root = Path(artifact_root).expanduser().resolve(strict=True)
    candidate = Path(path).expanduser().resolve(strict=True)
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError("evidence path 超出 artifact_root") from exc
    if not candidate.is_file():
        raise ValueError("evidence path 必须指向普通文件")
    return candidate.as_uri()


@dataclass
class Gate:
    """质量门禁：Step 完成前必须满足的条件"""

    must_produce: str | list[str] = ""  # 必须产出的 artifact key(s)
    min_length: int = 0  # artifact 最小字符数
    check_command: str = ""  # 可选：运行命令验证
    max_iterations: int = 0  # 可选：最大重试轮数（0=不限）
    on_failure: Optional[str] = None  # 失败时跳转的步骤 ID
    require_verified_evidence: bool = False
    allowed_verifiers: list[str] = field(default_factory=list)
    max_evidence_age_seconds: int = DEFAULT_MAX_EVIDENCE_AGE_SECONDS
    max_artifact_bytes: int = DEFAULT_MAX_ARTIFACT_BYTES

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

    def check(
        self, context: Dict[str, Any], *, artifact_root: str | Path | None = None
    ) -> Tuple[bool, str]:
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
                if self.require_verified_evidence:
                    return False, f"产出 '{artifact_key}' 的强门禁必须使用结构化证据"
                if not artifact:
                    return False, f"产出 '{artifact_key}' 不能为空"
                if self.min_length > 0 and len(artifact) < self.min_length:
                    return False, (
                        f"产出 '{artifact_key}' 长度 {len(artifact)} < {self.min_length}"
                    )
                continue

            valid, reason, size = self._validate_evidence(artifact, artifact_root=artifact_root)
            if not valid:
                return False, f"产出 '{artifact_key}' 的结构化证据无效: {reason}"
            if self.min_length > 0 and size < self.min_length:
                return False, f"产出 '{artifact_key}' 长度 {size} < {self.min_length}"

        return True, ""

    def _validate_evidence(
        self, evidence: dict[str, Any], *, artifact_root: str | Path | None
    ) -> tuple[bool, str, int]:
        evidence_type = evidence.get("type")
        if not isinstance(evidence_type, str) or not evidence_type.strip():
            return False, "缺少非空 type", 0
        if self.require_verified_evidence:
            if not self.allowed_verifiers:
                return False, "强门禁未配置 allowed_verifiers", 0
            for field_name in ("producer", "verified_by", "verified_at"):
                value = evidence.get(field_name)
                if not isinstance(value, str) or not value.strip():
                    return False, f"强门禁缺少 {field_name}", 0
            if evidence["verified_by"] not in self.allowed_verifiers:
                return False, "verified_by 不在允许的 verifier 列表中", 0
            try:
                verified_at = datetime.fromisoformat(evidence["verified_at"].replace("Z", "+00:00"))
            except ValueError:
                return False, "verified_at 必须是 ISO-8601 时间", 0
            if verified_at.tzinfo is None or verified_at.utcoffset() is None:
                return False, "verified_at 必须包含时区", 0
            now = datetime.now(timezone.utc)
            verified_at = verified_at.astimezone(timezone.utc)
            if verified_at > now + timedelta(seconds=MAX_EVIDENCE_FUTURE_SKEW_SECONDS):
                return False, "verified_at 不能是未来时间", 0
            if verified_at < now - timedelta(seconds=self.max_evidence_age_seconds):
                return False, "证据已超过允许的最大年龄", 0

        content = evidence.get("content")
        if content is not None and (not isinstance(content, (str, bytes)) or not content):
            return False, "content 必须是非空字符串或字节", 0
        digest = evidence.get("sha256")
        if digest is not None and (not isinstance(digest, str) or not SHA256_RE.fullmatch(digest)):
            return False, "sha256 必须是 64 位十六进制摘要", 0

        uri = evidence.get("uri")
        if uri is None:
            if not isinstance(content, (str, bytes)):
                return False, "必须提供非空 content 或 file:// URI", 0
            content_bytes = content.encode("utf-8") if isinstance(content, str) else content
            if len(content_bytes) > self.max_artifact_bytes:
                return False, f"content 超过 {self.max_artifact_bytes} 字节上限", 0
            if self.require_verified_evidence and digest is None:
                return False, "强门禁的 content evidence 必须提供 sha256", 0
            actual = hashlib.sha256(content_bytes).hexdigest()
            if digest is not None and digest.lower() != actual:
                return False, "sha256 与 content 不匹配", 0
            return True, "", len(content_bytes)

        if not isinstance(uri, str) or not uri.strip():
            return False, "uri 必须是非空 file:// URI", 0
        parsed = urlparse(uri)
        if parsed.scheme != "file" or not parsed.path:
            return False, "uri 必须使用 file:// 协议", 0
        root = Path(artifact_root or Path.cwd()).resolve()
        path = Path(unquote(parsed.path))
        try:
            relative = path.relative_to(root)
        except ValueError:
            return False, "file URI 超出允许的 artifact 根目录", 0
        if not relative.parts or any(part in {"", ".", ".."} for part in relative.parts):
            return False, "file URI 包含不安全的路径组件", 0
        if digest is None:
            return False, "file URI evidence 必须提供 sha256", 0
        try:
            descriptor = self._open_beneath_root(root, relative)
        except (FileNotFoundError, OSError, ValueError):
            return False, "file URI 不指向可读取的普通文件", 0
        try:
            before = os.fstat(descriptor)
            if not stat.S_ISREG(before.st_mode):
                return False, "file URI 不指向普通文件", 0
            if before.st_size > self.max_artifact_bytes:
                return False, f"artifact 超过 {self.max_artifact_bytes} 字节上限", 0
            hasher = hashlib.sha256()
            size = 0
            while True:
                chunk = os.read(descriptor, HASH_CHUNK_BYTES)
                if not chunk:
                    break
                size += len(chunk)
                if size > self.max_artifact_bytes:
                    return False, f"artifact 超过 {self.max_artifact_bytes} 字节上限", 0
                hasher.update(chunk)
            after = os.fstat(descriptor)
        finally:
            os.close(descriptor)
        if (
            before.st_dev,
            before.st_ino,
            before.st_size,
            before.st_mtime_ns,
        ) != (
            after.st_dev,
            after.st_ino,
            after.st_size,
            after.st_mtime_ns,
        ):
            return False, "artifact 在验证期间发生变化", 0
        if digest.lower() != hasher.hexdigest():
            return False, "sha256 与 file URI 内容不匹配", 0
        return True, "", size

    @staticmethod
    def _open_beneath_root(root: Path, relative: Path) -> int:
        """Open a file without following symlinks in any path component."""
        nofollow = getattr(os, "O_NOFOLLOW", 0)
        directory = getattr(os, "O_DIRECTORY", 0)
        root_fd = os.open(root, os.O_RDONLY | directory)
        current_fd = root_fd
        try:
            for part in relative.parts[:-1]:
                next_fd = os.open(
                    part,
                    os.O_RDONLY | directory | nofollow,
                    dir_fd=current_fd,
                )
                if current_fd != root_fd:
                    os.close(current_fd)
                current_fd = next_fd
            descriptor = os.open(
                relative.parts[-1],
                os.O_RDONLY | nofollow,
                dir_fd=current_fd,
            )
            return descriptor
        finally:
            if current_fd != root_fd:
                os.close(current_fd)
            os.close(root_fd)


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
    profile: str = "coordination"

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
        if self.profile not in {"coordination", "production"}:
            errors.append("profile 必须是 coordination 或 production")
        if self.profile == "production" and not self.steps:
            errors.append("Production Pipeline 至少需要一个 Step")

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
            if self.profile == "production":
                if step.skip_if:
                    errors.append(f"Production Step '{step.id}' 不允许使用 skip_if")
                if not step.gate:
                    errors.append(f"Production Step '{step.id}' 必须配置 gate")
                elif not (
                    step.gate.require_verified_evidence
                    and step.gate.allowed_verifiers
                    and step.gate.check_command
                ):
                    errors.append(
                        f"Production Step '{step.id}' 必须配置 require_verified_evidence、"
                        "allowed_verifiers 和 check_command"
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
    verification: Dict[str, Any] = field(default_factory=dict)
    approval_outbox: Dict[str, Any] = field(default_factory=dict)
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
                "verification": self.verification,
                "approval_outbox": self.approval_outbox,
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
            verification=data.get("verification", {}),
            approval_outbox=data.get("approval_outbox", {}),
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
