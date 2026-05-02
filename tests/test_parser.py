import pytest
import tempfile

from src.compiler.parser import Parser
from src.compiler.resolver import Resolver
from src.models import Zone, SkillMeta, Config, Rule


def test_combo_members_expansion():
    """测试 Combo 成员 skills 正确合并进结果"""
    yaml_content = """
version: "1.0"
zones:
  - id: default
    name: 默认区
    load_policy: free
    priority: 0
    rules: []
skills:
  - id: skill-a
    name: Skill A
    path: /path/a
    summary: A
    tags: [a]
  - id: skill-b
    name: Skill B
    path: /path/b
    summary: B
    tags: [b]
combos:
  - id: combo-ab
    name: Combo AB
    description: "A 和 B 的组合"
    members:
      - skill-a
      - skill-b
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(yaml_content)
        f.flush()

        config = Parser(f.name).parse()

        # Combo 成员应该存在于 skills 中
        skill_ids = {s.id for s in config.skills}
        assert "skill-a" in skill_ids
        assert "skill-b" in skill_ids

        # Combo 应该被正确解析，description 不丢失
        assert len(config.combos) == 1
        assert config.combos[0].id == "combo-ab"
        assert set(config.combos[0].members) == {"skill-a", "skill-b"}
        assert config.combos[0].description == "A 和 B 的组合"


def test_default_zone_selection_prefers_id_over_no_rules():
    """default_zone 应优先选 id='default' 的 zone，而非第一个无 rules 的 zone"""
    yaml_content = """
version: "1.0"
zones:
  - id: no-rules-zone
    name: 无 rules 区（不应被选为 default）
    load_policy: free
    priority: 0
    rules: []
  - id: default
    name: 真正的默认区
    load_policy: free
    priority: 0
    rules: []
skills:
  - id: skill-a
    name: Skill A
    path: /path/a
    summary: A
    tags: [a]
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(yaml_content)
        f.flush()
        config = Parser(f.name).parse()
        assert config.default_zone is not None
        assert config.default_zone.id == "default"


def test_exclusive_zone_filters_skills():
    """测试 exclusive Zone 只保留本 Zone skills + 白名单"""
    zone_enterprise = Zone(
        id="enterprise",
        name="企业区",
        load_policy="exclusive",
        priority=100,
        rules=[Rule(pattern="*/enterprise/*")],
        allow_base_skills=["base-skill"],
    )

    zone_default = Zone(
        id="default",
        name="默认区",
        load_policy="free",
        priority=0,
        rules=[],
    )

    skill_enterprise = SkillMeta(
        id="enterprise-skill",
        name="企业技能",
        path="/path/e",
        summary="E",
        zones=["enterprise"],
        load_policy="require",
        priority=100,
    )

    skill_base = SkillMeta(
        id="base-skill",
        name="基础技能",
        path="/path/b",
        summary="B",
        zones=["default"],
        load_policy="free",
        priority=50,
    )

    skill_other = SkillMeta(
        id="other-skill",
        name="其他技能",
        path="/path/o",
        summary="O",
        zones=["default"],
        load_policy="free",
        priority=10,
    )

    config = Config(
        zones=[zone_enterprise, zone_default],
        skills=[skill_enterprise, skill_base, skill_other],
        default_zone=zone_default,
    )

    resolver = Resolver(config)
    resolved = resolver.resolve(zone_enterprise)

    # enterprise-skill 应该在 forced 中
    forced_ids = {s.id for s in resolved.forced_skills}
    assert "enterprise-skill" in forced_ids

    # base-skill 应该在 passive 中（白名单）
    passive_ids = {s.id for s in resolved.passive_skills}
    assert "base-skill" in passive_ids

    # other-skill 不应该在结果中
    all_ids = forced_ids | passive_ids | {s.id for s in resolved.blocked_skills}
    assert "other-skill" not in all_ids


def test_skill_base_field_parsed_from_frontmatter(tmp_path):
    """base 字段应从 .md frontmatter 解析并存入 SkillMeta.base"""
    base_md = tmp_path / "base-skill.md"
    base_md.write_text("---\nid: base-skill\nname: Base\nsummary: base content\n---\n# Base\n")

    derived_md = tmp_path / "derived-skill.md"
    derived_md.write_text(
        "---\nid: derived-skill\nname: Derived\nsummary: derived\nbase: base-skill\n---\n# Derived\n"
    )

    yaml_content = f"""
version: "1.0"
zones:
  - id: default
    name: 默认区
    load_policy: free
    priority: 0
    rules: []
skill_dirs:
  - {str(tmp_path)}
"""
    config_file = tmp_path / "skills.yaml"
    config_file.write_text(yaml_content)

    config = Parser(str(config_file)).parse()
    skill_map = {s.id: s for s in config.skills}

    assert "derived-skill" in skill_map
    assert skill_map["derived-skill"].base == "base-skill"
    assert skill_map["base-skill"].base == ""


def test_resolver_rejects_nonexistent_base(tmp_path):
    """base 指向不存在的 skill 应在 resolve() 时报错"""
    md = tmp_path / "orphan.md"
    md.write_text("---\nid: orphan\nname: Orphan\nsummary: s\nbase: ghost-skill\n---\n")

    yaml_content = f"""
version: "1.0"
zones:
  - id: default
    name: 默认区
    load_policy: free
    priority: 0
    rules: []
skill_dirs:
  - {str(tmp_path)}
"""
    config_file = tmp_path / "skills.yaml"
    config_file.write_text(yaml_content)

    config = Parser(str(config_file)).parse()
    with pytest.raises(ValueError, match="ghost-skill"):
        Resolver(config).resolve()


def test_resolver_rejects_cyclic_base(tmp_path):
    """循环继承（A → B → A）应在 resolve() 时报错"""
    (tmp_path / "skill-a.md").write_text(
        "---\nid: skill-a\nname: A\nsummary: a\nbase: skill-b\n---\n"
    )
    (tmp_path / "skill-b.md").write_text(
        "---\nid: skill-b\nname: B\nsummary: b\nbase: skill-a\n---\n"
    )

    yaml_content = f"""
version: "1.0"
zones:
  - id: default
    name: 默认区
    load_policy: free
    priority: 0
    rules: []
skill_dirs:
  - {str(tmp_path)}
"""
    config_file = tmp_path / "skills.yaml"
    config_file.write_text(yaml_content)

    config = Parser(str(config_file)).parse()
    with pytest.raises(ValueError, match="循环继承"):
        Resolver(config).resolve()


def test_exclusive_zone_no_skills_fallback():
    """测试 exclusive Zone 无 skill 时回退 default + 打印 WARNING"""
    zone_empty = Zone(
        id="empty-zone",
        name="空区",
        load_policy="exclusive",
        priority=100,
        rules=[Rule(pattern="*/empty/*")],
        allow_base_skills=[],
    )

    zone_default = Zone(
        id="default",
        name="默认区",
        load_policy="free",
        priority=0,
        rules=[],
    )

    skill = SkillMeta(
        id="default-skill",
        name="默认技能",
        path="/path/d",
        summary="D",
        zones=["default"],
        load_policy="free",
        priority=10,
    )

    config = Config(
        zones=[zone_empty, zone_default],
        skills=[skill],
        default_zone=zone_default,
    )

    resolver = Resolver(config)

    # 当 exclusive Zone 无 skill 时，应该回退到 default
    resolved = resolver.resolve(zone_empty)

    # 应该使用 default zone
    assert resolved.active_zone == zone_empty
    # 但 skills 应该来自 default
    assert len(resolved.forced_skills) + len(resolved.passive_skills) == 0
