"""Zone 和 Rule 数据模型"""

from dataclasses import dataclass, field
from typing import List


@dataclass
class Rule:
    """Zone 匹配规则"""

    pattern: str = ""  # glob 路径匹配，如 "*/internal/*"
    git_contains: str = ""  # git config 包含的字符串，如 "company.com"

    def __post_init__(self):
        if not self.pattern and not self.git_contains:
            raise ValueError("Rule 必须至少指定 pattern 或 git_contains")


@dataclass
class Zone:
    """区域定义"""

    id: str
    name: str
    load_policy: str  # require / exclusive / free
    priority: int  # 0-999，数值越高优先级越高
    rules: List[Rule] = field(default_factory=list)
    skills: List[str] = field(default_factory=list)  # 该 Zone 强制加载的 skill IDs
    allow_base_skills: List[str] = field(default_factory=list)  # exclusive 时的白名单

    def __post_init__(self):
        valid_policies = ("require", "exclusive", "free")
        if self.load_policy not in valid_policies:
            raise ValueError(f"load_policy 必须是 {valid_policies} 之一")
        if not 0 <= self.priority <= 999:
            raise ValueError("priority 必须在 0-999 范围内")
