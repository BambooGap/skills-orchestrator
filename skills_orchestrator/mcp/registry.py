"""SkillRegistry — 运行时 skill 注册表，从 compiler 加载，惰性缓存内容"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from skills_orchestrator.compiler.parser import Parser
from skills_orchestrator.compiler.resolver import Resolver
from skills_orchestrator.models import SkillMeta, Config, Combo


class SkillRegistry:
    """
    运行时 skill 注册表。

    - 启动时通过 Parser + Resolver 加载所有 skill 元数据
    - skill 完整内容惰性读取（仅 get_skill 时才读文件）
    - 支持热重载（reload()）
    """

    def __init__(self, config_path: str, zone_id: str | None = None):
        self._config_path = config_path
        self._zone_id = zone_id
        self._skills: dict[str, SkillMeta] = {}
        self._all_skills: dict[str, SkillMeta] = {}  # 全量索引（用于 base 继承）
        self._combos: list[Combo] = []
        self._content_cache: dict[str, str] = {}
        self._load()

    def _load(self) -> None:
        parser = Parser(self._config_path)
        config: Config = parser.parse()

        # 全量索引（仅用于 base 继承解析）
        self._all_skills = {s.id: s for s in config.skills}

        resolver = Resolver(config)

        # 解析 zone
        zone = None
        if self._zone_id:
            zone = next((z for z in config.zones if z.id == self._zone_id), None)
            if zone is None:
                raise ValueError(f"未知 zone: {self._zone_id}")

        resolved = resolver.resolve(zone)

        # zone 过滤索引（用于 list/search/MCP 暴露）
        self._skills = {}
        for skill in resolved.forced_skills + resolved.passive_skills:
            self._skills[skill.id] = skill

        self._combos = config.combos
        self._content_cache = {}
        self._base_dir = resolved.base_dir  # 项目根目录，用于解析相对路径

        # required_on_start: 预热缓存（reduce first-call latency）
        for skill in resolved.forced_skills:
            self._warm(skill)

    def reload(self) -> None:
        """热重载：重新扫描 skill 文件，不重启 server"""
        self._content_cache.clear()
        self._load()

    # ── 查询接口 ──────────────────────────────────────────────────

    def all(self) -> list[SkillMeta]:
        return list(self._skills.values())

    def combos(self) -> list[Combo]:
        return list(self._combos)

    def get_meta(self, skill_id: str) -> Optional[SkillMeta]:
        return self._skills.get(skill_id)

    def _resolve_path(self, skill_path: str) -> Path:
        """将 skill.path 解析为绝对路径（相对路径以项目根目录为基准）。"""
        p = Path(skill_path)
        if p.is_absolute():
            return p
        base = getattr(self, "_base_dir", None) or str(Path(self._config_path).parent)
        return (Path(base) / p).resolve()

    def get_content(self, skill_id: str) -> Optional[str]:
        """返回 skill 完整 .md 内容（带缓存）。

        公共入口：只能读取当前 zone 可见 skill。
        """
        if skill_id not in self._skills:
            return None
        return self._get_content_internal(skill_id, allow_all_for_base=True)

    def _get_content_internal(
        self, skill_id: str, _chain: tuple[str, ...] = (), allow_all_for_base: bool = False
    ) -> Optional[str]:
        """内部读取方法，支持 base 继承。

        Args:
            skill_id: skill 唯一标识
            _chain: 循环继承检测链
            allow_all_for_base: 是否允许从全量索引读取（用于 base 继承）
        """
        if skill_id in self._content_cache:
            return self._content_cache[skill_id]

        # 先从当前 zone 查找
        skill = self._skills.get(skill_id)

        # 如果允许访问全量索引（用于 base 继承）
        if skill is None and allow_all_for_base:
            skill = self._all_skills.get(skill_id)

        if skill is None:
            return None

        path = self._resolve_path(skill.path)
        if not path.exists():
            return f"> 文件不存在: {skill.path}"

        raw = path.read_text(encoding="utf-8")

        if skill.base:
            if skill.base in _chain:
                # 循环继承保护：直接返回原始内容
                content = raw
            else:
                base_content = self._get_content_internal(
                    skill.base, _chain + (skill_id,), allow_all_for_base=True
                )
                if base_content:
                    body = self._strip_frontmatter(raw)
                    content = base_content + "\n\n---\n\n" + body
                else:
                    content = raw
        else:
            content = raw

        self._content_cache[skill_id] = content
        return content

    @staticmethod
    def _strip_frontmatter(content: str) -> str:
        """移除 YAML frontmatter（--- ... ---），返回正文。"""
        if not content.startswith("---"):
            return content
        end = content.find("\n---", 3)
        if end == -1:
            return content
        return content[end + 4 :].lstrip()

    def _warm(self, skill: SkillMeta) -> None:
        self._get_content_internal(skill.id, allow_all_for_base=True)
