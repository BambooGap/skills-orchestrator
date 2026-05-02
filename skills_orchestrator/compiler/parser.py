"""Parser - YAML 解析 + 路径变量展开 + Combo 展开 + skill_dirs 自动发现"""

import os
from pathlib import Path

import yaml

from skills_orchestrator.models import Zone, Rule, SkillMeta, Combo, Config


class Parser:
    """解析 skills.yaml 配置文件"""

    def __init__(self, config_path: str):
        self.config_path = Path(config_path)
        # 配置文件所在目录，用于解析 skill_dirs 等相对路径
        self.config_dir = self.config_path.parent
        # 项目根目录（用于存储可移植的相对路径），parse() 时根据 skill_dirs 自动计算
        self.base_dir = self.config_dir.resolve()

    def parse(self) -> Config:
        if not self.config_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {self.config_path}")

        with open(self.config_path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f)

        if not raw:
            raise ValueError("配置文件为空")

        zones = self._parse_zones(raw.get("zones", []))

        # 先算项目根目录：config_dir 与所有 skill_dirs 的最低公共祖先
        # 这样 _discover_from_dirs 里 _skill_from_file 存的就是相对路径
        project_root = self._compute_project_root(raw)
        self.base_dir = project_root

        # ── 两种 skill 来源，可以同时存在 ──────────────────────────
        # 1. skill_dirs：自动发现（新格式）
        # 2. skills：手动注册列表（旧格式，向后兼容）
        auto_skills: list[SkillMeta] = []
        if "skill_dirs" in raw:
            auto_skills = self._discover_from_dirs(raw["skill_dirs"])
            overrides = raw.get("overrides", [])
            auto_skills = self._apply_overrides(auto_skills, overrides)

        explicit_skills = self._parse_skills(raw.get("skills", []))

        # 合并：auto_skills 优先，explicit 补充（id 不重复）
        auto_ids = {s.id for s in auto_skills}
        extra = [s for s in explicit_skills if s.id not in auto_ids]
        skills = auto_skills + extra

        combos = self._parse_combos(raw.get("combos", []))
        skills = self._expand_combos(skills, combos)

        # 优先找 id="default" 的 zone，找不到再退回第一个无 rules 的 zone
        default_zone = next((z for z in zones if z.id == "default"), None) or next(
            (z for z in zones if not z.rules), None
        )

        return Config(
            zones=zones,
            skills=skills,
            combos=combos,
            default_zone=default_zone,
            base_dir=str(project_root),
        )

    # ── Auto-Discovery ───────────────────────────────────────────

    def _discover_from_dirs(self, skill_dirs: list[str]) -> list[SkillMeta]:
        """递归扫描 skill_dirs，从 frontmatter 解析 skill 元数据。"""
        skills: list[SkillMeta] = []
        seen_ids: set[str] = set()

        for dir_expr in skill_dirs:
            dir_path = (self.config_dir / self._expand_path(dir_expr)).resolve()
            if not dir_path.exists():
                raise FileNotFoundError(f"skill_dirs 目录不存在: {dir_path}")

            # 递归扫描所有 .md 文件
            for md_file in sorted(dir_path.rglob("*.md")):
                skill = self._skill_from_file(md_file)
                if skill.id in seen_ids:
                    continue  # 同 id 只取第一个（先声明的目录优先）
                seen_ids.add(skill.id)
                skills.append(skill)

        return skills

    def _skill_from_file(self, md_file: Path) -> SkillMeta:
        """从 .md 文件解析 SkillMeta，frontmatter 优先，否则从内容推断。"""
        content = md_file.read_text(encoding="utf-8")
        meta = self._read_frontmatter(content)

        skill_id = meta.get("id", md_file.stem)
        name = meta.get("name", md_file.stem.replace("-", " ").title())

        # description 是 karpathy-skills 等外部仓库的字段名
        summary = meta.get("summary") or meta.get("description", "")

        tags = meta.get("tags", [])
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(",") if t.strip()]

        load_policy = meta.get("load_policy", "free")
        priority = int(meta.get("priority", 50))
        zones = meta.get("zones", ["default"])
        if isinstance(zones, str):
            zones = [zones]
        conflict_with = meta.get("conflict_with", [])
        if isinstance(conflict_with, str):
            conflict_with = [conflict_with]

        base = meta.get("base", "")

        # 存相对于项目根目录的路径，保证项目可移植
        try:
            stored_path = str(md_file.relative_to(self.base_dir))
        except ValueError:
            stored_path = str(md_file)  # 在项目根外时回退绝对路径

        return SkillMeta(
            id=skill_id,
            name=name,
            path=stored_path,
            summary=summary,
            tags=tags,
            load_policy=load_policy,
            priority=priority,
            zones=zones,
            conflict_with=conflict_with,
            base=base,
        )

    @staticmethod
    def _read_frontmatter(content: str) -> dict:
        """解析 YAML frontmatter（--- ... ---），失败返回空 dict。"""
        if not content.startswith("---"):
            return {}
        end = content.find("\n---", 3)
        if end == -1:
            return {}
        try:
            meta = yaml.safe_load(content[3:end]) or {}
            return meta if isinstance(meta, dict) else {}
        except yaml.YAMLError:
            return {}

    def _apply_overrides(self, skills: list[SkillMeta], overrides: list[dict]) -> list[SkillMeta]:
        """用 yaml overrides 段覆盖自动发现的字段（只写例外，不写所有人）。"""
        override_map = {o["id"]: o for o in overrides if "id" in o}
        result = []
        for skill in skills:
            if skill.id not in override_map:
                result.append(skill)
                continue
            o = override_map[skill.id]
            result.append(
                SkillMeta(
                    id=skill.id,
                    name=o.get("name", skill.name),
                    path=skill.path,
                    summary=o.get("summary", skill.summary),
                    tags=o.get("tags", skill.tags),
                    load_policy=o.get("load_policy", skill.load_policy),
                    priority=o.get("priority", skill.priority),
                    zones=o.get("zones", skill.zones),
                    conflict_with=o.get("conflict_with", skill.conflict_with),
                    base=skill.base,  # base 只从文件 frontmatter 读取，不可被 overrides 覆盖
                )
            )
        return result

    # ── 旧格式解析（向后兼容）───────────────────────────────────

    def _parse_zones(self, raw_zones: list) -> list[Zone]:
        zones = []
        for raw in raw_zones:
            rules = [
                Rule(
                    pattern=r.get("pattern", ""),
                    git_contains=r.get("git_contains", ""),
                )
                for r in raw.get("rules", [])
            ]
            zones.append(
                Zone(
                    id=raw["id"],
                    name=raw["name"],
                    load_policy=raw["load_policy"],
                    priority=raw["priority"],
                    rules=rules,
                    skills=raw.get("skills", []),
                    allow_base_skills=raw.get("allow_base_skills", []),
                )
            )
        return zones

    def _parse_skills(self, raw_skills: list) -> list[SkillMeta]:
        skills = []
        for raw in raw_skills:
            path = self._expand_path(raw["path"])
            skills.append(
                SkillMeta(
                    id=raw["id"],
                    name=raw["name"],
                    path=path,
                    summary=raw["summary"],
                    tags=raw.get("tags", []),
                    load_policy=raw.get("load_policy", "free"),
                    priority=raw.get("priority", 0),
                    zones=raw.get("zones", []),
                    conflict_with=raw.get("conflict_with", []),
                    base=raw.get("base", ""),
                )
            )
        return skills

    def _parse_combos(self, raw_combos: list) -> list[Combo]:
        return [
            Combo(
                id=raw["id"],
                name=raw["name"],
                members=raw.get("members", raw.get("skills", [])),
                description=raw.get("description", ""),
            )
            for raw in raw_combos
        ]

    def _expand_path(self, path: str) -> str:
        return os.path.expanduser(os.path.expandvars(path))

    def _compute_project_root(self, raw: dict) -> Path:
        """计算项目根目录：config_dir 与所有 skill_dirs resolve 后的最低公共祖先。

        这样存储的 skill.path（如 skills/coding/tdd.md）相对于项目根，
        整个项目目录可移植（git clone 到哪都能用）。
        """
        config_dir = self.config_dir.resolve()
        paths = [config_dir]

        for dir_expr in raw.get("skill_dirs", []):
            resolved = (config_dir / self._expand_path(dir_expr)).resolve()
            if resolved.exists():
                paths.append(resolved)

        # 找所有路径的最低公共祖先
        if len(paths) < 2:
            return config_dir

        # 取所有路径的 parts 交集
        common = list(paths[0].parts)
        for p in paths[1:]:
            new_common = []
            for a, b in zip(common, p.parts):
                if a == b:
                    new_common.append(a)
                else:
                    break
            common = new_common
            if not common:
                break

        if not common:
            return config_dir

        return Path(*common)

    def _expand_combos(self, skills: list[SkillMeta], combos: list[Combo]) -> list[SkillMeta]:
        skill_ids = {s.id for s in skills}
        for combo in combos:
            for skill_id in combo.members:
                if skill_id not in skill_ids:
                    raise ValueError(f"Combo '{combo.id}' 引用了不存在的 skill: {skill_id}")
        return skills
