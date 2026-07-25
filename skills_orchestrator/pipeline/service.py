"""Transactional Pipeline execution shared by CLI and MCP entry points."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol
import uuid

from .engine import PipelineEngine
from .models import Pipeline, RunState
from .store import RunStateStore


class AuditSink(Protocol):
    @property
    def enabled(self) -> bool: ...

    @property
    def audit_dir(self) -> Path | None: ...

    def append(self, event: dict[str, Any], *, strict: bool = False) -> dict[str, Any] | None: ...


class ProductionAuditError(RuntimeError):
    """A production run cannot persist its mandatory audit event."""

    def __init__(self, message: str, *, code: str):
        super().__init__(message)
        self.code = code


class PipelineRunService:
    """Own lease, verification, audit, and state commit ordering."""

    def __init__(
        self,
        pipeline: Pipeline,
        store: RunStateStore,
        *,
        artifact_root: str | Path | None = None,
        audit: AuditSink | None = None,
    ):
        self.pipeline = pipeline
        self.store = store
        self.engine = PipelineEngine(
            pipeline,
            artifact_root=artifact_root,
            allow_production_execution=True,
        )
        self.audit = audit

    def start(self, context: dict[str, Any] | None = None) -> RunState:
        state = self.engine.start(context=context)
        self._append_production_event(
            {
                "event": "pipeline_run_started",
                "outcome": "pending_commit",
                "pipeline_id": state.pipeline_id,
                "run_id": state.run_id,
                "step_id": state.current_step,
            }
        )
        self.store.save(state)
        return state

    def advance(
        self,
        state: RunState,
        *,
        context_updates: dict[str, Any] | None = None,
    ) -> RunState:
        self._require_production_audit()
        if self.pipeline.profile == "production" and state.approval_outbox:
            state = self._flush_approval_outbox(state)
            if state.status in {"completed", "failed"}:
                return state
        if context_updates:
            state.context.update(context_updates)

        execution_id: str | None = None
        binding: dict[str, str] | None = None
        current = self.pipeline.get_step(state.current_step) if state.current_step else None
        if current and current.gate and current.gate.check_command:
            execution_id = self.store.claim_verification(state, current.id)
            if self.pipeline.profile == "production":
                binding, _ = self.engine._production_verifier_binding(state, current, execution_id)

        state = self.engine.complete_and_advance(state, execution_id=execution_id)
        if self.pipeline.profile == "production":
            event: dict[str, Any] = {
                "event_id": uuid.uuid4().hex,
                "event": "pipeline_step_evaluated",
                "outcome": "gate_failed" if state.status == "failed" else "gate_passed",
                "pipeline_id": state.pipeline_id,
                "run_id": state.run_id,
                "step_id": current.id if current else None,
                "execution_id": execution_id,
            }
            if binding:
                event.update(
                    {
                        "evidence_digest": binding["evidence_digest"],
                        "verifier": binding["verifier"],
                    }
                )
            assert self.audit is not None
            assert self.audit.audit_dir is not None
            state.verification = {}
            state.approval_outbox = {
                "event_id": event["event_id"],
                "audit_dir": str(self.audit.audit_dir),
                "candidate_status": state.status,
                "event": event,
            }
            # The candidate state and its recovery record must be durable before
            # an audit event is allowed to claim the gate outcome.
            self.store.save(state)
            self._append_production_event(event)
            return state

        state.verification = {}
        self.store.save(state)
        return state

    def _flush_approval_outbox(self, state: RunState) -> RunState:
        outbox = state.approval_outbox
        event = outbox.get("event")
        candidate_status = outbox.get("candidate_status")
        if not isinstance(event, dict) or not isinstance(candidate_status, str):
            raise ProductionAuditError(
                "Production approval outbox 无效，无法恢复",
                code="PRODUCTION_OUTBOX_INVALID",
            )
        self._append_production_event(event)
        state.status = candidate_status
        state.approval_outbox = {}
        try:
            self.store.save(state)
        except Exception as exc:
            raise ProductionAuditError(
                f"Production approval outbox 清理失败: {exc}",
                code="PRODUCTION_OUTBOX_CLEANUP_FAILED",
            ) from exc
        return state

    def _require_production_audit(self) -> None:
        if self.pipeline.profile == "production" and (self.audit is None or not self.audit.enabled):
            raise ProductionAuditError(
                "Production Pipeline 必须配置可写的 audit_dir",
                code="PRODUCTION_AUDIT_REQUIRED",
            )

    def _append_production_event(self, event: dict[str, Any]) -> None:
        if self.pipeline.profile != "production":
            return
        self._require_production_audit()
        assert self.audit is not None
        try:
            self.audit.append(event, strict=True)
        except Exception as exc:
            raise ProductionAuditError(
                f"Production audit 写入失败: {exc}",
                code="PRODUCTION_AUDIT_WRITE_FAILED",
            ) from exc
