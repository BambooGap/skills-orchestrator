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

AUDIT_DIR_ENV = "SKILLS_ORCHESTRATOR_AUDIT_DIR"
AUDIT_SALT_ENV = "SKILLS_ORCHESTRATOR_AUDIT_SALT"
EVENTS_FILENAME = "events.jsonl"


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
    def events_path(self) -> Path | None:
        if self._audit_dir is None:
            return None
        return self._audit_dir / EVENTS_FILENAME

    def append(self, event: dict[str, Any]) -> None:
        """Append one audit event. Logging failures are intentionally non-fatal."""
        path = self.events_path
        if path is None:
            return
        try:
            path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            path.parent.chmod(0o700)
            payload = {"timestamp": utc_now_iso(), **event}
            with path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")
            path.chmod(0o600)
        except OSError:
            return


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


def load_events(audit_dir: str | os.PathLike[str] | None = None) -> list[dict[str, Any]]:
    """Load well-formed JSONL audit events from the configured audit directory."""
    path = resolve_audit_dir(audit_dir)
    if path is None:
        return []

    events_path = path / EVENTS_FILENAME
    if not events_path.exists():
        return []

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
