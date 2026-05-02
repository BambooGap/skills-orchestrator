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
                gate = Gate(
                    must_produce=gate_raw.get("must_produce", ""),
                    min_length=gate_raw.get("min_length", 0),
                    check_command=gate_raw.get("check_command", ""),
                    max_iterations=gate_raw.get("max_iterations", 0),
                )
            step = Step(
                id=step_raw["id"],
                skill=step_raw["skill"],
                next=step_raw.get("next", []),
                skip_if=step_raw.get("skip_if"),
                gate=gate,
            )
            steps.append(step)

        return Pipeline(
            id=raw["id"],
            name=raw["name"],
            description=raw.get("description", ""),
            steps=steps,
        )

    def validate_skills(self, pipeline: Pipeline, known_skills: Set[str]) -> List[str]:
        """检查 Pipeline 引用的 skill 是否存在，返回缺失的 skill ID 列表"""
        missing: List[str] = []
        for step in pipeline.steps:
            if step.skill not in known_skills:
                missing.append(step.skill)
        return missing
