"""Manifest 相关数据模型"""

from dataclasses import dataclass, field
from typing import List, Optional

from .zone import Zone
from .skill import SkillMeta
from .combo import Combo


@dataclass
class Config:
    """解析后的配置对象"""

    zones: List[Zone] = field(default_factory=list)
    skills: List[SkillMeta] = field(default_factory=list)
    combos: List[Combo] = field(default_factory=list)
    default_zone: Optional[Zone] = None  # 无规则匹配时的兜底区域
    base_dir: str = ""  # skills.yaml 所在目录，用于解析相对 skill 路径


@dataclass
class ResolvedConfig:
    """冲突解决后的配置对象"""

    forced_skills: List[SkillMeta] = field(default_factory=list)  # load_policy=require
    passive_skills: List[SkillMeta] = field(default_factory=list)  # load_policy=free
    blocked_skills: List[SkillMeta] = field(default_factory=list)  # 被冲突拦截
    combos: List[Combo] = field(default_factory=list)
    active_zone: Optional[Zone] = None
    block_reasons: dict = field(default_factory=dict)  # {skill_id: 拦截原因}
    base_dir: str = ""  # 透传自 Config，供 Compressor 解析相对路径


@dataclass
class Manifest:
    """最终输出的清单"""

    forced_content: str = ""  # 强制 skills 完整内容
    passive_index: str = ""  # 可选 skills 压缩摘要
    blocked_list: List[str] = field(default_factory=list)  # 被拦截的 skill ID


@dataclass
class LoadPlan:
    """运行时加载计划"""

    forced: str  # 强制注入内容
    passive_index: str  # 被动索引
    blocked: List[str]  # 拦截列表
    active_zone: str  # 当前生效的 Zone ID