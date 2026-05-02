"""Combo 数据模型"""

from dataclasses import dataclass, field
from typing import List


@dataclass
class Combo:
    """组合声明 - 编译时语法糖，展开为成员 skills"""

    id: str
    name: str
    members: List[str] = field(default_factory=list)  # 成员 skill ID 列表
    description: str = ""  # 供 MCP suggest_combo 展示

    def __post_init__(self):
        if not self.members:
            raise ValueError("Combo 必须至少包含一个 skill")
