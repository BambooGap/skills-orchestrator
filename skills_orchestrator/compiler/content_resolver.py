"""SkillContentResolver — 统一的内容读取入口

所有 skill 内容读取（build / sync / MCP / pipeline）都应走此模块，
保证 base 继承合并、缓存、frontmatter 处理的逻辑一致。

设计：
- resolver = SkillContentResolver(base_dir=...)
- resolver.read(skill) → 完整内容（含 base 继承合并）
- 可选传入 SkillRegistry 来复用其缓存
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from skills_orchestrator.models import SkillMeta
    from skills_orchestrator.mcp.registry import SkillRegistry


class SkillContentResolver:
    """统一 skill 内容读取器。

    优先级：
    1. 如果传入了 registry，走 registry.get_content()（有缓存 + base 继承合并）
    2. 否则直接读文件，并自行处理 base 继承合并
    """

    def __init__(
        self,
        base_dir: str,
        registry: Optional[SkillRegistry] = None,
        skills: Optional[list[SkillMeta]] = None,
        all_skills: Optional[list[SkillMeta]] = None,
    ):
        """
        Args:
            base_dir: 项目根目录，用于解析相对 skill 路径
            registry: 可选 SkillRegistry 实例，传入后复用其缓存和继承逻辑
            skills: 当前 zone 可见的 skill 列表（用于查找 base）
            all_skills: 全量 skill 列表（用于跨 Zone base 继承）
        """
        self._base_dir = base_dir
        self._registry = registry
        # skills: 当前 zone 可见（用于对外读取）
        self._skills = {s.id: s for s in (skills or [])}
        # all_skills: 全量索引（用于 base 继承）
        self._all_skills = {s.id: s for s in (all_skills or skills or [])}
        self._cache: dict[str, str] = {}  # 仅在无 registry 时使用

    def read(self, skill: SkillMeta) -> str:
        """读取 skill 完整内容（含 base 继承合并）。

        Args:
            skill: SkillMeta 实例

        Returns:
            skill 的完整 markdown 内容
        """
        # 优先走 registry（有缓存 + 已实现 base 合并）
        if self._registry is not None:
            try:
                content = self._registry.get_content(skill.id)
                if content:
                    return content
            except Exception:
                pass  # registry 失败时降级

        # 检查本地缓存
        if skill.id in self._cache:
            return self._cache[skill.id]

        # 直接读文件
        path = self._resolve_path(skill.path)
        if not path.exists():
            result = f"> 文件不存在: {skill.path}"
            self._cache[skill.id] = result
            return result

        raw = path.read_text(encoding="utf-8")

        # base 继承合并
        if skill.base:
            base_content = self._read_base(skill.base, chain=(skill.id,))
            if base_content:
                body = self._strip_frontmatter(raw)
                result = base_content + "\n\n---\n\n" + body
            else:
                result = raw
        else:
            result = raw

        self._cache[skill.id] = result
        return result

    def _read_base(self, base_id: str, chain: tuple[str, ...] = ()) -> Optional[str]:
        """读取 base skill 的内容，支持循环检测。

        优先走 registry 的 get_base_content()（支持跨 Zone），否则尝试从全量 skill 列表找到 base skill 再读取。
        """
        if base_id in chain:
            return None  # 循环继承保护

        # 优先走 registry（使用内部方法支持跨 Zone base）
        if self._registry is not None:
            try:
                # 尝试使用内部方法 get_base_content()
                if hasattr(self._registry, "get_base_content"):
                    content = self._registry.get_base_content(base_id, chain)
                else:
                    # 兼容旧版 registry（不支持 _chain 参数）
                    content = self._registry.get_content(base_id)
                if content:
                    return content
            except Exception:
                pass

        # 检查缓存
        if base_id in self._cache:
            return self._cache[base_id]

        # 从全量 skill 列表找到 base skill 的元数据，然后读取
        base_meta = self._all_skills.get(base_id)
        if base_meta:
            return self.read(base_meta)

        return None

    def _resolve_path(self, skill_path: str) -> Path:
        """将 skill.path 解析为绝对路径"""
        p = Path(skill_path)
        if p.is_absolute():
            return p
        return (Path(self._base_dir) / p).resolve()

    @staticmethod
    def _strip_frontmatter(content: str) -> str:
        """移除 YAML frontmatter（--- ... ---），返回正文。"""
        if not content.startswith("---"):
            return content
        end = content.find("\n---", 3)
        if end == -1:
            return content
        return content[end + 4 :].lstrip()
