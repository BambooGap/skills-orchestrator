"""Append-only MCP audit events for team runtime governance."""

from __future__ import annotations

import json
import os
import hmac
import hashlib
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import fcntl
except ImportError:  # pragma: no cover - production MCP runtime is POSIX.
    fcntl = None  # type: ignore[assignment]

AUDIT_DIR_ENV = "SKILLS_ORCHESTRATOR_AUDIT_DIR"
AUDIT_SALT_ENV = "SKILLS_ORCHESTRATOR_AUDIT_SALT"
EVENTS_FILENAME = "events.jsonl"
AUDIT_LOCK_FILENAME = ".events.lock"


class AuditWriteError(RuntimeError):
    """Raised when a mandatory production audit event cannot be persisted."""


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def resolve_audit_dir(audit_dir: str | os.PathLike[str] | None = None) -> Path | None:
    """Return the configured audit directory, or None when audit logging is disabled."""
    configured = audit_dir or os.environ.get(AUDIT_DIR_ENV)
    if not configured:
        return None
    return Path(configured).expanduser()


class AuditLogger:
    """Best-effort JSONL logger that avoids storing raw task text or skill content."""

    def __init__(self, audit_dir: str | os.PathLike[str] | None = None):
        self._audit_dir = resolve_audit_dir(audit_dir)

    @property
    def enabled(self) -> bool:
        return self._audit_dir is not None

    @property
    def audit_dir(self) -> Path | None:
        return self._audit_dir

    @property
    def events_path(self) -> Path | None:
        if self._audit_dir is None:
            return None
        return self._audit_dir / EVENTS_FILENAME

    def append(self, event: dict[str, Any], *, strict: bool = False) -> dict[str, Any] | None:
        """Append one hash-chained event.

        Coordination-mode callers keep best-effort behavior. Production callers
        use ``strict=True`` so a missing or failed audit sink stops approval.
        """
        path = self.events_path
        if path is None:
            if strict:
                raise AuditWriteError("Production Pipeline 必须配置可写的 audit_dir")
            return None
        try:
            path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            path.parent.chmod(0o700)
            lock_path = path.parent / AUDIT_LOCK_FILENAME
            with lock_path.open("a+", encoding="utf-8") as lock:
                if fcntl is not None:
                    fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
                events = self._verify_chain_path(path)
                event_id = event.get("event_id")
                if event_id:
                    existing = next(
                        (item for item in events if item.get("event_id") == event_id),
                        None,
                    )
                    if existing is not None:
                        stored_event = {
                            key: value
                            for key, value in existing.items()
                            if key
                            not in {
                                "timestamp",
                                "sequence",
                                "previous_event_hash",
                                "event_hash",
                            }
                        }
                        if stored_event != event:
                            raise ValueError(f"audit event_id={event_id!r} 已存在但事件内容不一致")
                        return existing
                previous = events[-1] if events else None
                sequence = int(previous.get("sequence", 0)) + 1 if previous else 1
                previous_hash = str(previous.get("event_hash", "")) if previous else ""
                payload = {
                    **event,
                    "timestamp": utc_now_iso(),
                    "sequence": sequence,
                    "previous_event_hash": previous_hash,
                }
                canonical = json.dumps(
                    payload,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode("utf-8")
                payload["event_hash"] = hashlib.sha256(canonical).hexdigest()
                with path.open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")
                    handle.flush()
                    os.fsync(handle.fileno())
                if fcntl is not None:
                    fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
            path.chmod(0o600)
            return payload
        except (OSError, ValueError, TypeError) as exc:
            if strict:
                raise AuditWriteError(f"Production audit 写入失败: {exc}") from exc
            return None

    def verify_chain(self) -> list[dict[str, Any]]:
        """Validate the complete JSONL chain and return its events."""
        path = self.events_path
        if path is None:
            return []
        return self._verify_chain_path(path)

    def contains_event(self, event_id: str) -> bool:
        """Return whether a valid chain contains an event with this stable id."""
        return any(event.get("event_id") == event_id for event in self.verify_chain())

    @staticmethod
    def _verify_chain_path(path: Path) -> list[dict[str, Any]]:
        if not path.exists():
            return []
        events: list[dict[str, Any]] = []
        expected_previous_hash = ""
        with path.open(encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                event = json.loads(line)
                if not isinstance(event, dict):
                    raise ValueError(f"audit 第 {line_number} 行不是 JSON object")
                expected_sequence = len(events) + 1
                if event.get("sequence") != expected_sequence:
                    raise ValueError(
                        f"audit sequence 不连续: expected {expected_sequence}, "
                        f"got {event.get('sequence')}"
                    )
                if event.get("previous_event_hash") != expected_previous_hash:
                    raise ValueError(f"audit 第 {line_number} 行的 previous_event_hash 不匹配")
                recorded_hash = event.get("event_hash")
                if not isinstance(recorded_hash, str) or not recorded_hash:
                    raise ValueError(f"audit 第 {line_number} 行缺少 event_hash")
                unhashed = {key: value for key, value in event.items() if key != "event_hash"}
                canonical = json.dumps(
                    unhashed,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode("utf-8")
                calculated = hashlib.sha256(canonical).hexdigest()
                if not hmac.compare_digest(recorded_hash, calculated):
                    raise ValueError(f"audit 第 {line_number} 行哈希校验失败")
                events.append(event)
                expected_previous_hash = recorded_hash
        return events


def hash_task(task: str) -> dict[str, str]:
    """Return a task hash without storing raw task text.

    Set SKILLS_ORCHESTRATOR_AUDIT_SALT to use HMAC-SHA256 and avoid dictionary
    matching across audit logs. Unsalted SHA-256 remains the default for
    backwards-compatible local correlation.
    """
    salt = os.environ.get(AUDIT_SALT_ENV)
    if salt:
        digest = hmac.new(salt.encode("utf-8"), task.encode("utf-8"), hashlib.sha256).hexdigest()
        return {"alg": "HMAC-SHA256", "value": digest}
    return {"alg": "SHA-256", "value": hashlib.sha256(task.encode("utf-8")).hexdigest()}


def load_events(
    audit_dir: str | os.PathLike[str] | None = None,
    *,
    best_effort: bool = False,
) -> list[dict[str, Any]]:
    """Load audit events, verifying the complete chain unless explicitly relaxed."""
    path = resolve_audit_dir(audit_dir)
    if path is None:
        return []

    events_path = path / EVENTS_FILENAME
    if not events_path.exists():
        return []
    if not best_effort:
        return AuditLogger(path).verify_chain()

    events: list[dict[str, Any]] = []
    with events_path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(event, dict):
                events.append(event)
    return events


def summarize_events(events: list[dict[str, Any]]) -> dict[str, Any]:
    """Summarize MCP audit events for a compact team usage report."""
    tool_counts: Counter[str] = Counter()
    outcome_counts: Counter[str] = Counter()
    skill_counts: Counter[str] = Counter()
    no_result_searches = 0

    for event in events:
        tool = event.get("tool")
        if event.get("event") == "mcp_tool_call" and isinstance(tool, str):
            tool_counts[tool] += 1

        outcome = event.get("outcome")
        if isinstance(outcome, str):
            outcome_counts[outcome] += 1

        for skill_id in event.get("active_skill_ids") or []:
            if isinstance(skill_id, str):
                skill_counts[skill_id] += 1

        if event.get("tool") == "search_skills" and event.get("result_count") == 0:
            no_result_searches += 1

    return {
        "events": len(events),
        "tools": dict(tool_counts.most_common()),
        "outcomes": dict(outcome_counts.most_common()),
        "top_active_skills": dict(skill_counts.most_common(10)),
        "searches_with_no_result": no_result_searches,
    }
