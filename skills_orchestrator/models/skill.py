"""SkillMeta 数据模型"""

from dataclasses import dataclass, field
from typing import List


@dataclass
class SkillMeta:
    """技能元数据"""

    id: str
    name: str
    path: str  # 支持 ${ENV_VAR} 和相对路径
    summary: str
    tags: List[str] = field(default_factory=list)
    load_policy: str = "free"  # require / free
    priority: int = 0
    zones: List[str] = field(default_factory=list)
    conflict_with: List[str] = field(default_factory=list)
    base: str = ""  # base skill ID for content inheritance

    def __post_init__(self):
        valid_policies = ("require", "free")
        if self.load_policy not in valid_policies:
            raise ValueError(f"load_policy 必须是 {valid_policies} 之一")
        if not 0 <= self.priority <= 999:
            raise ValueError("priority 必须在 0-999 范围内")
