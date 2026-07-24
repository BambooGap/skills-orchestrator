"""RunState 持久化存储 — 保存/恢复 Pipeline 运行状态"""

from __future__ import annotations

import json
import os
import re
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Dict, List, Optional

try:  # POSIX is the supported production runtime for the bundled MCP server.
    import fcntl
except ImportError:  # pragma: no cover - exercised only on unsupported runtimes.
    fcntl = None  # type: ignore[assignment]

from skills_orchestrator.security import safe_child_path, validate_identifier

from .models import RunState

STATE_FILENAME_RE = re.compile(
    r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}_[A-Za-z0-9][A-Za-z0-9_-]{0,63}\.json$"
)
STATE_DIR_ENV = "SKILLS_ORCHESTRATOR_STATE_DIR"


class ConcurrentStateError(RuntimeError):
    """Raised when a caller tries to overwrite a newer persisted RunState."""


class RunStateStore:
    """RunState 文件持久化

    目录结构:
        base_dir/
          runs/
            {pipeline_id}_{run_id}.json
          latest -> 符号链接或记录文件
    """

    def __init__(self, base_dir: Optional[str] = None):
        if base_dir is None:
            base_dir = os.environ.get(STATE_DIR_ENV) or os.path.expanduser("~/.skills-orchestrator")
        self.base_dir = Path(base_dir)
        self.runs_dir = self.base_dir / "runs"
        self.runs_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.runs_dir.chmod(0o700)

    def save(self, state: RunState) -> Path:
        """保存 RunState 到文件，返回文件路径"""
        filepath = self._state_path(state.pipeline_id, state.run_id)
        with self._write_lock():
            current_revision = 0
            if filepath.exists():
                current_revision = RunState.from_json(filepath.read_text(encoding="utf-8")).revision
            if state.revision != current_revision:
                raise ConcurrentStateError(
                    f"运行状态已被其他调用者更新（expected revision {state.revision}, "
                    f"current {current_revision}）"
                )
            state.revision = current_revision + 1
            self._atomic_write(filepath, state.to_json())
            # 更新 latest 记录必须与状态文件同一把锁，避免引用未提交状态。
            self._update_latest(state)
        return filepath

    def load(self, pipeline_id: str, run_id: str) -> Optional[RunState]:
        """根据 pipeline_id 和 run_id 加载 RunState"""
        filepath = self._state_path(pipeline_id, run_id)
        if not filepath.exists():
            return None
        return RunState.from_json(filepath.read_text(encoding="utf-8"))

    def load_latest(self, pipeline_id: Optional[str] = None) -> Optional[RunState]:
        """加载最近一次运行的 RunState

        如果指定 pipeline_id，只返回该 pipeline 的最近运行。
        """
        latest_file = self.runs_dir / ".latest"
        if latest_file.exists():
            ref = latest_file.read_text(encoding="utf-8").strip()
            if not STATE_FILENAME_RE.fullmatch(ref):
                raise ValueError(f"非法 latest 记录: {ref!r}")
            filepath = safe_child_path(self.runs_dir, ref)
            if filepath.exists():
                state = RunState.from_json(filepath.read_text(encoding="utf-8"))
                if pipeline_id is None or state.pipeline_id == self._validate_pipeline_id(
                    pipeline_id
                ):
                    return state

        # fallback: 遍历文件按修改时间排序
        candidates = list(self.runs_dir.glob("*.json"))
        if not candidates:
            return None
        candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        for filepath in candidates:
            state = RunState.from_json(filepath.read_text(encoding="utf-8"))
            if pipeline_id is None or state.pipeline_id == self._validate_pipeline_id(pipeline_id):
                return state
        return None

    def list_runs(self, pipeline_id: Optional[str] = None) -> List[Dict]:
        """列出所有运行记录，返回摘要列表

        每条记录: {"pipeline_id", "run_id", "status", "current_step", "started_at", "updated_at"}
        """
        results = []
        for filepath in sorted(self.runs_dir.glob("*.json"), reverse=True):
            try:
                state = RunState.from_json(filepath.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, KeyError):
                continue
            if pipeline_id and state.pipeline_id != self._validate_pipeline_id(pipeline_id):
                continue
            results.append(
                {
                    "pipeline_id": state.pipeline_id,
                    "run_id": state.run_id,
                    "status": state.status,
                    "current_step": state.current_step,
                    "started_at": state.started_at,
                    "updated_at": state.updated_at,
                }
            )
        return results

    def delete(self, pipeline_id: str, run_id: str) -> bool:
        """删除指定运行记录"""
        filepath = self._state_path(pipeline_id, run_id)
        with self._write_lock():
            if filepath.exists():
                filepath.unlink()
                return True
            return False

    def _update_latest(self, state: RunState) -> None:
        """更新 .latest 记录文件"""
        pipeline_id = self._validate_pipeline_id(state.pipeline_id)
        run_id = self._validate_run_id(state.run_id)
        filename = f"{pipeline_id}_{run_id}.json"
        latest_file = self.runs_dir / ".latest"
        self._atomic_write(latest_file, filename)

    def _atomic_write(self, path: Path, content: str) -> None:
        """Durably replace one state file without exposing partial JSON to readers."""
        descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=self.runs_dir)
        temporary = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            temporary.chmod(0o600)
            os.replace(temporary, path)
            path.chmod(0o600)
            directory_fd = os.open(self.runs_dir, os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        finally:
            if temporary.exists():
                temporary.unlink()

    @contextmanager
    def _write_lock(self):
        """Serialize writers across MCP processes before applying revision CAS."""
        if fcntl is None:  # pragma: no cover - unsupported runtime must not fail open.
            raise RuntimeError("RunStateStore requires POSIX file locking for writes")
        lock_path = self.runs_dir / ".state.lock"
        with lock_path.open("a+", encoding="utf-8") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

    @staticmethod
    def _validate_pipeline_id(pipeline_id: str) -> str:
        return validate_identifier(pipeline_id, "pipeline_id")

    @staticmethod
    def _validate_run_id(run_id: str) -> str:
        return validate_identifier(run_id, "run_id")

    def _state_path(self, pipeline_id: str, run_id: str) -> Path:
        pipeline_id = self._validate_pipeline_id(pipeline_id)
        run_id = self._validate_run_id(run_id)
        return safe_child_path(self.runs_dir, f"{pipeline_id}_{run_id}.json")
