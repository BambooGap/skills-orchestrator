"""Pipeline 加载器 — 从 YAML 文件加载 Pipeline 定义"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Set

import yaml

from .models import Gate, Pipeline, Step


class PipelineLoader:
    """从 YAML 文件加载和验证 Pipeline"""

    def load(self, path: str) -> Pipeline:
        """加载 YAML 并返回 Pipeline 对象"""
        raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
        return self._parse(raw)

    def load_string(self, yaml_str: str) -> Pipeline:
        """从 YAML 字符串加载"""
        raw = yaml.safe_load(yaml_str)
        return self._parse(raw)

    def _parse(self, raw: Dict) -> Pipeline:
        """解析 YAML 字典为 Pipeline 对象"""
        steps: List[Step] = []
        for step_raw in raw.get("steps", []):
            gate: Optional[Gate] = None
            gate_raw = step_raw.get("gate")
            if gate_raw and isinstance(gate_raw, dict):
                check_command = gate_raw.get("check_command", "")
                if not isinstance(check_command, str):
                    raise ValueError(f"Step '{step_raw['id']}' 的 gate.check_command 必须是字符串")
                require_verified_evidence = gate_raw.get("require_verified_evidence", False)
                if not isinstance(require_verified_evidence, bool):
                    raise ValueError(
                        f"Step '{step_raw['id']}' 的 gate.require_verified_evidence 必须是 boolean"
                    )
                allowed_verifiers = gate_raw.get("allowed_verifiers", [])
                if not isinstance(allowed_verifiers, list) or not all(
                    isinstance(item, str) and item.strip() for item in allowed_verifiers
                ):
                    raise ValueError(
                        f"Step '{step_raw['id']}' 的 gate.allowed_verifiers 必须是非空字符串列表"
                    )
                max_evidence_age_seconds = gate_raw.get("max_evidence_age_seconds", 86_400)
                max_artifact_bytes = gate_raw.get("max_artifact_bytes", 20 * 1024 * 1024)
                if (
                    not isinstance(max_evidence_age_seconds, int)
                    or isinstance(max_evidence_age_seconds, bool)
                    or max_evidence_age_seconds <= 0
                ):
                    raise ValueError(
                        f"Step '{step_raw['id']}' 的 gate.max_evidence_age_seconds 必须是正整数"
                    )
                if (
                    not isinstance(max_artifact_bytes, int)
                    or isinstance(max_artifact_bytes, bool)
                    or max_artifact_bytes <= 0
                ):
                    raise ValueError(
                        f"Step '{step_raw['id']}' 的 gate.max_artifact_bytes 必须是正整数"
                    )
                gate = Gate(
                    must_produce=gate_raw.get("must_produce", ""),
                    min_length=gate_raw.get("min_length", 0),
                    check_command=check_command,
                    max_iterations=gate_raw.get("max_iterations", 0),
                    on_failure=gate_raw.get("on_failure"),  # 新增
                    require_verified_evidence=require_verified_evidence,
                    allowed_verifiers=allowed_verifiers,
                    max_evidence_age_seconds=max_evidence_age_seconds,
                    max_artifact_bytes=max_artifact_bytes,
                )
            step = Step(
                id=step_raw["id"],
                skill=step_raw["skill"],
                next=self._parse_next(step_raw.get("next", []), step_raw["id"]),
                skip_if=step_raw.get("skip_if"),
                gate=gate,
                on_gate_failure=step_raw.get("on_gate_failure"),  # 新增
            )
            steps.append(step)

        pipeline = Pipeline(
            id=raw["id"],
            name=raw["name"],
            description=raw.get("description", ""),
            profile=raw.get("profile", "coordination"),
            steps=steps,
        )
        errors = pipeline.validate()
        if errors:
            raise ValueError("Pipeline 定义无效: " + "; ".join(errors))
        return pipeline

    def _parse_next(self, raw_next: object, step_id: str) -> List[str]:
        """Normalize next edges from YAML.

        The documented form is `next: [step_id]`, but accepting `next: step_id`
        prevents a common YAML authoring mistake from becoming a character-level
        edge list.
        """
        if raw_next is None:
            return []
        if isinstance(raw_next, str):
            return [raw_next]
        if isinstance(raw_next, list) and all(isinstance(item, str) for item in raw_next):
            return raw_next
        raise ValueError(f"Step '{step_id}' 的 next 必须是字符串或字符串列表")

    def validate_skills(self, pipeline: Pipeline, known_skills: Set[str]) -> List[str]:
        """检查 Pipeline 引用的 skill 是否存在，返回缺失的 skill ID 列表"""
        missing: List[str] = []
        for step in pipeline.steps:
            if step.skill not in known_skills:
                missing.append(step.skill)
        return missing
