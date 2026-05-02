"""Resolver - 冲突检测 + 优先级排序"""

from typing import List, Optional

from src.models import Zone, SkillMeta, Config, ResolvedConfig


class Resolver:
    """冲突解决器"""

    def __init__(self, config: Config):
        self.config = config

    def resolve(self, zone: Optional[Zone] = None) -> ResolvedConfig:
        """解析冲突，返回 ResolvedConfig"""
        # 确定当前 Zone
        active_zone = zone or self.config.default_zone

        # 按 Zone 过滤 skills
        zone_skills = self._filter_by_zone(active_zone)

        # 验证 base 引用
        self._validate_bases(zone_skills)

        # 检测冲突
        forced, passive, blocked, block_reasons = self._detect_conflicts(zone_skills)

        return ResolvedConfig(
            forced_skills=forced,
            passive_skills=passive,
            blocked_skills=blocked,
            combos=self.config.combos,
            active_zone=active_zone,
            block_reasons=block_reasons,
            base_dir=self.config.base_dir,
        )

    def _validate_bases(self, skills: List[SkillMeta]) -> None:
        """验证 base 引用存在且无循环。"""
        all_ids = {s.id for s in self.config.skills}
        base_map = {s.id: s.base for s in skills if s.base}

        for skill_id, base_id in base_map.items():
            if base_id not in all_ids:
                raise ValueError(
                    f"skill '{skill_id}' 的 base '{base_id}' 不存在，"
                    f"请检查 frontmatter 中的 base 字段。"
                )

        # 循环检测：DFS
        def has_cycle(start: str, visited: set) -> bool:
            if start in visited:
                return True
            b = base_map.get(start, "")
            if not b:
                return False
            return has_cycle(b, visited | {start})

        for skill_id in base_map:
            if has_cycle(skill_id, set()):
                raise ValueError(f"skill '{skill_id}' 存在循环继承，请检查 base 引用链。")

    def _filter_by_zone(self, zone: Optional[Zone]) -> List[SkillMeta]:
        """按 Zone 过滤 skills"""
        if not zone:
            return self.config.skills

        # Zone 指定了 skills 列表时，只返回这些 skills
        if zone.skills:
            zone_skill_ids = set(zone.skills)
            # exclusive 模式：加入白名单
            if zone.load_policy == "exclusive":
                zone_skill_ids.update(zone.allow_base_skills)
            return [s for s in self.config.skills if s.id in zone_skill_ids]

        # exclusive Zone：只保留该 Zone skills + 白名单
        if zone.load_policy == "exclusive":
            allowed_ids = set(zone.allow_base_skills)
            return [s for s in self.config.skills if zone.id in s.zones or s.id in allowed_ids]

        # 其他 Zone：保留属于该 Zone 的 skills 或未指定 Zone 的 skills
        return [s for s in self.config.skills if zone.id in s.zones or not s.zones]

    def _detect_conflicts(
        self, skills: List[SkillMeta]
    ) -> tuple[List[SkillMeta], List[SkillMeta], List[SkillMeta], dict]:
        """检测冲突并分类，返回 (forced, passive, blocked, block_reasons)"""
        forced = []
        passive = []
        blocked = []
        blocked_ids: set[str] = set()
        block_reasons: dict[str, str] = {}

        skill_map = {s.id: s for s in skills}

        for skill in skills:
            if skill.id in blocked_ids:
                continue

            conflict_found = False
            for conflict_id in skill.conflict_with:
                if conflict_id in skill_map:
                    other = skill_map[conflict_id]
                    winner = self._resolve_conflict(skill, other)
                    if winner is None:
                        raise ValueError(
                            f"{skill.id} 与 {conflict_id} 互相冲突（均为 require 级别，无法自动裁决）\n"
                            f"  {skill.id} priority={skill.priority}"
                            f"  ↔  {conflict_id} priority={other.priority}\n"
                            f"\n修复方案（三选一）：\n"
                            f"  1. 调优先级：将 {skill.id} 的 priority 改为"
                            f" {other.priority + 1} 或更高\n"
                            f"  2. 降策略：将 {conflict_id} 的 load_policy 改为 free\n"
                            f"  3. 删声明：如两者实际不冲突，删除 conflict_with 声明"
                        )
                    if winner == skill:
                        blocked_ids.add(conflict_id)
                        block_reasons[conflict_id] = (
                            f"被 {skill.id} 拦截"
                            f" (policy={skill.load_policy}, priority={skill.priority}"
                            f" > {other.priority})"
                        )
                    else:
                        blocked_ids.add(skill.id)
                        block_reasons[skill.id] = (
                            f"被 {conflict_id} 拦截"
                            f" (policy={other.load_policy}, priority={other.priority}"
                            f" >= {skill.priority})"
                        )
                        conflict_found = True
                        break

            if not conflict_found and skill.id not in blocked_ids:
                if skill.load_policy == "require":
                    forced.append(skill)
                else:
                    passive.append(skill)

        for skill in skills:
            if skill.id in blocked_ids:
                blocked.append(skill)

        forced.sort(key=lambda s: -s.priority)
        passive.sort(key=lambda s: -s.priority)

        return forced, passive, blocked, block_reasons

    def _resolve_conflict(self, skill1: SkillMeta, skill2: SkillMeta) -> Optional[SkillMeta]:
        """解决两个 skill 之间的冲突，返回胜者；若无法决定返回 None"""
        # load_policy 权重
        policy_weight = {"require": 2, "free": 1}

        w1 = policy_weight.get(skill1.load_policy, 1)
        w2 = policy_weight.get(skill2.load_policy, 1)

        if w1 > w2:
            return skill1
        elif w2 > w1:
            return skill2

        # 同权重，比较 priority
        if skill1.priority > skill2.priority:
            return skill1
        elif skill2.priority > skill1.priority:
            return skill2

        # 同 priority，且都是 require → 无法自动解决
        if skill1.load_policy == "require":
            return None

        # 同 priority，都是 free → 保留第一个
        return skill1
