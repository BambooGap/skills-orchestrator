from pathlib import Path
from unittest.mock import patch

from skills_orchestrator.models import Zone, Rule, Config, Manifest
from skills_orchestrator.enforcer import Enforcer


def _make_config(zones):
    default = next((z for z in zones if z.id == "default"), None)
    return Config(zones=zones, default_zone=default)


def test_detect_zone_by_glob():
    """glob 路径匹配命中正确 Zone"""
    zone = Zone(
        id="work",
        name="Work",
        priority=10,
        rules=[Rule(pattern="*/projects/work/*")],
        load_policy="free",
    )
    default = Zone(id="default", name="默认", priority=0, load_policy="free")
    cfg = _make_config([zone, default])
    enforcer = Enforcer(cfg, Manifest())

    with patch(
        "skills_orchestrator.enforcer.Path.resolve",
        return_value=Path("/home/user/projects/work/app"),
    ):
        result = enforcer.detect_zone("/home/user/projects/work/app")

    assert result.id == "work"


def test_detect_zone_fallback_to_default():
    """无规则匹配时回退 default Zone"""
    zone = Zone(
        id="work",
        name="Work",
        priority=10,
        rules=[Rule(pattern="*/projects/work/*")],
        load_policy="free",
    )
    default = Zone(id="default", name="默认", priority=0, load_policy="free")
    cfg = _make_config([zone, default])
    enforcer = Enforcer(cfg, Manifest())

    result = enforcer.detect_zone("/home/user/projects/personal/blog")
    assert result.id == "default"


def test_detect_zone_priority_order():
    """高 priority Zone 优先匹配"""
    low = Zone(
        id="low",
        name="Low",
        priority=1,
        rules=[Rule(pattern="*/projects/*")],
        load_policy="free",
    )
    high = Zone(
        id="high",
        name="High",
        priority=100,
        rules=[Rule(pattern="*/projects/*")],
        load_policy="exclusive",
    )
    default = Zone(id="default", name="默认", priority=0, load_policy="free")
    cfg = _make_config([low, high, default])
    enforcer = Enforcer(cfg, Manifest())

    with patch(
        "skills_orchestrator.enforcer.Path.resolve", return_value=Path("/home/user/projects/foo")
    ):
        result = enforcer.detect_zone("/home/user/projects/foo")

    assert result.id == "high"


def test_detect_zone_git_contains(tmp_path):
    """git_contains 匹配仓库根目录的 marker 文件"""
    # 创建 marker 文件
    (tmp_path / ".enterprise").write_text("", encoding="utf-8")

    zone = Zone(
        id="enterprise",
        name="Enterprise",
        priority=50,
        rules=[Rule(git_contains=".enterprise")],
        load_policy="exclusive",
    )
    default = Zone(id="default", name="默认", priority=0, load_policy="free")
    cfg = _make_config([zone, default])
    enforcer = Enforcer(cfg, Manifest())

    result = enforcer.detect_zone(str(tmp_path))
    assert result.id == "enterprise"


def test_apply_returns_load_plan():
    """apply() 返回正确的 LoadPlan"""
    default = Zone(id="default", name="默认", priority=0, load_policy="free")
    cfg = _make_config([default])
    manifest = Manifest(
        forced_content="forced content",
        passive_index="| skill | desc | tags |",
        blocked_list=["blocked-skill"],
    )
    enforcer = Enforcer(cfg, manifest)

    plan = enforcer.apply("/any/path")
    assert plan.active_zone == "default"
    assert plan.forced == "forced content"
    assert plan.blocked == ["blocked-skill"]
