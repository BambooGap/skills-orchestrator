import pytest
from skills_orchestrator.models import Zone, SkillMeta, Config, Rule
from skills_orchestrator.compiler.resolver import Resolver


def test_conflict_resolution():
    """测试冲突解决"""
    zone = Zone(id="default", name="默认区", load_policy="free", priority=0)

    skill1 = SkillMeta(
        id="skill-a",
        name="Skill A",
        path="/path/a",
        summary="A",
        load_policy="require",
        priority=100,
        zones=["default"],
        conflict_with=["skill-b"],
    )

    skill2 = SkillMeta(
        id="skill-b",
        name="Skill B",
        path="/path/b",
        summary="B",
        load_policy="free",
        priority=50,
        zones=["default"],
        conflict_with=[],
    )

    config = Config(zones=[zone], skills=[skill1, skill2])
    resolver = Resolver(config)
    resolved = resolver.resolve(zone)

    # skill-a 应该胜出（require > free）
    assert len(resolved.forced_skills) == 1
    assert resolved.forced_skills[0].id == "skill-a"
    assert len(resolved.blocked_skills) == 1
    assert resolved.blocked_skills[0].id == "skill-b"


def test_require_conflict_error():
    """测试两个 require 互冲突时报错"""
    zone = Zone(id="default", name="默认区", load_policy="free", priority=0)

    skill1 = SkillMeta(
        id="skill-a",
        name="Skill A",
        path="/path/a",
        summary="A",
        load_policy="require",
        priority=100,
        zones=["default"],
        conflict_with=["skill-b"],
    )

    skill2 = SkillMeta(
        id="skill-b",
        name="Skill B",
        path="/path/b",
        summary="B",
        load_policy="require",
        priority=100,
        zones=["default"],
        conflict_with=["skill-a"],
    )

    config = Config(zones=[zone], skills=[skill1, skill2])
    resolver = Resolver(config)

    with pytest.raises(ValueError, match="互相冲突"):
        resolver.resolve(zone)


def test_priority_wins_on_same_policy():
    """测试相同 load_policy 时 priority 高者胜"""
    zone = Zone(id="default", name="默认区", load_policy="free", priority=0)

    skill_high = SkillMeta(
        id="high-priority",
        name="High Priority",
        path="/path/h",
        summary="H",
        load_policy="free",
        priority=100,
        zones=["default"],
        conflict_with=["low-priority"],
    )

    skill_low = SkillMeta(
        id="low-priority",
        name="Low Priority",
        path="/path/l",
        summary="L",
        load_policy="free",
        priority=50,
        zones=["default"],
        conflict_with=[],
    )

    config = Config(zones=[zone], skills=[skill_high, skill_low])
    resolver = Resolver(config)
    resolved = resolver.resolve(zone)

    # 高优先级应该胜出
    passive_ids = {s.id for s in resolved.passive_skills}
    assert "high-priority" in passive_ids
    assert "low-priority" not in passive_ids

    # 低优先级应该在 blocked 中
    blocked_ids = {s.id for s in resolved.blocked_skills}
    assert "low-priority" in blocked_ids


def test_exclusive_zone_with_whitelist():
    """测试 exclusive Zone 保留白名单 skills"""
    zone_exclusive = Zone(
        id="exclusive-zone",
        name="独占区",
        load_policy="exclusive",
        priority=100,
        rules=[Rule(pattern="*/exclusive/*")],
        allow_base_skills=["base-skill"],
    )

    skill_exclusive = SkillMeta(
        id="exclusive-skill",
        name="独占技能",
        path="/path/e",
        summary="E",
        load_policy="require",
        priority=100,
        zones=["exclusive-zone"],
    )

    skill_base = SkillMeta(
        id="base-skill",
        name="基础技能",
        path="/path/b",
        summary="B",
        load_policy="free",
        priority=50,
        zones=["default"],
    )

    skill_other = SkillMeta(
        id="other-skill",
        name="其他技能",
        path="/path/o",
        summary="O",
        load_policy="free",
        priority=10,
        zones=["default"],
    )

    config = Config(
        zones=[zone_exclusive],
        skills=[skill_exclusive, skill_base, skill_other],
    )

    resolver = Resolver(config)
    resolved = resolver.resolve(zone_exclusive)

    # exclusive-skill 应该在 forced 中
    forced_ids = {s.id for s in resolved.forced_skills}
    assert "exclusive-skill" in forced_ids

    # base-skill 应该在 passive 中（白名单）
    passive_ids = {s.id for s in resolved.passive_skills}
    assert "base-skill" in passive_ids

    # other-skill 不应该出现
    all_ids = forced_ids | passive_ids | {s.id for s in resolved.blocked_skills}
    assert "other-skill" not in all_ids


def test_zone_require_upgrades_free_to_forced():
    """Zone load_policy=require 时，free skill 自动升级为 forced"""
    zone_require = Zone(
        id="enterprise",
        name="企业强制区",
        load_policy="require",
        priority=200,
    )

    # 这个 skill 自己是 free，属于 enterprise zone
    skill_free_in_enterprise = SkillMeta(
        id="code-review",
        name="Code Review",
        path="/path/cr",
        summary="CR",
        load_policy="free",
        priority=80,
        zones=["enterprise"],
    )

    # 这个 skill 自己已经是 require
    skill_require = SkillMeta(
        id="chinese-review",
        name="Chinese Review",
        path="/path/chr",
        summary="CHR",
        load_policy="require",
        priority=200,
        zones=["enterprise"],
    )

    config = Config(
        zones=[zone_require],
        skills=[skill_free_in_enterprise, skill_require],
    )
    resolver = Resolver(config)
    resolved = resolver.resolve(zone_require)

    # 两个 skill 都应该在 forced 中
    forced_ids = {s.id for s in resolved.forced_skills}
    assert "code-review" in forced_ids, "free skill 在 require zone 下应升级为 forced"
    assert "chinese-review" in forced_ids
    assert len(resolved.passive_skills) == 0


def test_zone_free_does_not_upgrade():
    """Zone load_policy=free 时，free skill 保持 passive"""
    zone_free = Zone(
        id="default",
        name="默认区",
        load_policy="free",
        priority=0,
    )

    skill_free = SkillMeta(
        id="tdd",
        name="TDD",
        path="/path/tdd",
        summary="TDD",
        load_policy="free",
        priority=90,
        zones=["default"],
    )

    config = Config(zones=[zone_free], skills=[skill_free])
    resolver = Resolver(config)
    resolved = resolver.resolve(zone_free)

    # free skill 在 free zone 下应该是 passive
    assert len(resolved.forced_skills) == 0
    assert len(resolved.passive_skills) == 1
    assert resolved.passive_skills[0].id == "tdd"
