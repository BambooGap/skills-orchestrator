"""skills.lock 测试"""

import json
import tempfile
from pathlib import Path

from skills_orchestrator.compiler.lock import SkillsLock, LockEntry
from skills_orchestrator.models import Zone, SkillMeta, ResolvedConfig


def _make_skill_file(tmpdir: Path, skill_id: str, content: str) -> str:
    """创建临时 skill 文件，返回路径"""
    path = tmpdir / f"{skill_id}.md"
    path.write_text(content, encoding="utf-8")
    return str(path)


def _make_resolved(tmpdir: Path, skills: list[SkillMeta]) -> ResolvedConfig:
    """构造 ResolvedConfig 用于测试"""
    return ResolvedConfig(
        forced_skills=[s for s in skills if s.load_policy == "require"],
        passive_skills=[s for s in skills if s.load_policy == "free"],
        blocked_skills=[],
        combos=[],
        active_zone=Zone(id="default", name="默认区", load_policy="free", priority=0),
        block_reasons={},
        base_dir=str(tmpdir),
    )


class TestLockEntry:
    def test_to_dict_and_from_dict(self):
        entry = LockEntry(
            id="tdd",
            name="TDD",
            path="/path/tdd.md",
            content_hash="abc123",
            load_policy="free",
            priority=90,
            zones=["default"],
            base="",
        )
        d = entry.to_dict()
        restored = LockEntry.from_dict(d)
        assert restored.id == "tdd"
        assert restored.content_hash == "abc123"


class TestSkillsLock:
    def test_generate_and_write(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            path1 = _make_skill_file(tmpdir, "tdd", "---\nid: tdd\n---\n# TDD")
            path2 = _make_skill_file(
                tmpdir, "review", "---\nid: review\nload_policy: require\n---\n# Review"
            )

            skills = [
                SkillMeta(
                    id="tdd",
                    name="TDD",
                    path=path1,
                    summary="TDD",
                    load_policy="free",
                    priority=90,
                    zones=["default"],
                ),
                SkillMeta(
                    id="review",
                    name="Review",
                    path=path2,
                    summary="Review",
                    load_policy="require",
                    priority=100,
                    zones=["default"],
                ),
            ]
            resolved = _make_resolved(tmpdir, skills)

            lock = SkillsLock(resolved)
            lock_path = lock.write(str(tmpdir / "skills.lock.json"))

            data = json.loads(Path(lock_path).read_text(encoding="utf-8"))
            assert data["version"] == "1.0"
            assert data["zone"] == "default"
            assert len(data["skills"]) == 2

            # forced skill (review) 在前
            skill_ids = [s["id"] for s in data["skills"]]
            assert "tdd" in skill_ids
            assert "review" in skill_ids

    def test_check_no_changes(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            path1 = _make_skill_file(tmpdir, "tdd", "---\nid: tdd\n---\n# TDD Content")

            skills = [
                SkillMeta(
                    id="tdd",
                    name="TDD",
                    path=path1,
                    summary="TDD",
                    load_policy="free",
                    priority=90,
                    zones=["default"],
                ),
            ]
            resolved = _make_resolved(tmpdir, skills)

            lock = SkillsLock(resolved)
            lock_path = lock.write(str(tmpdir / "skills.lock.json"))

            # 重新 resolve 同样的内容
            issues = SkillsLock.check(resolved, lock_path)
            assert len(issues) == 0

    def test_check_content_changed(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            path1 = _make_skill_file(tmpdir, "tdd", "---\nid: tdd\n---\n# TDD Original")

            skills = [
                SkillMeta(
                    id="tdd",
                    name="TDD",
                    path=path1,
                    summary="TDD",
                    load_policy="free",
                    priority=90,
                    zones=["default"],
                ),
            ]
            resolved = _make_resolved(tmpdir, skills)

            lock = SkillsLock(resolved)
            lock_path = lock.write(str(tmpdir / "skills.lock.json"))

            # 修改文件内容
            Path(path1).write_text("---\nid: tdd\n---\n# TDD Modified", encoding="utf-8")

            issues = SkillsLock.check(resolved, lock_path)
            assert len(issues) == 1
            assert "内容已变化" in issues[0]

    def test_check_skill_added(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            path1 = _make_skill_file(tmpdir, "tdd", "---\nid: tdd\n---\n# TDD")

            skills1 = [
                SkillMeta(
                    id="tdd",
                    name="TDD",
                    path=path1,
                    summary="TDD",
                    load_policy="free",
                    priority=90,
                    zones=["default"],
                ),
            ]
            resolved1 = _make_resolved(tmpdir, skills1)
            lock = SkillsLock(resolved1)
            lock_path = lock.write(str(tmpdir / "skills.lock.json"))

            # 新增一个 skill
            path2 = _make_skill_file(tmpdir, "review", "---\nid: review\n---\n# Review")
            skills2 = skills1 + [
                SkillMeta(
                    id="review",
                    name="Review",
                    path=path2,
                    summary="Review",
                    load_policy="free",
                    priority=80,
                    zones=["default"],
                ),
            ]
            resolved2 = _make_resolved(tmpdir, skills2)

            issues = SkillsLock.check(resolved2, lock_path)
            assert len(issues) == 1
            assert "新增 skill" in issues[0]

    def test_check_skill_removed(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            path1 = _make_skill_file(tmpdir, "tdd", "---\nid: tdd\n---\n# TDD")
            path2 = _make_skill_file(tmpdir, "review", "---\nid: review\n---\n# Review")

            skills1 = [
                SkillMeta(
                    id="tdd",
                    name="TDD",
                    path=path1,
                    summary="TDD",
                    load_policy="free",
                    priority=90,
                    zones=["default"],
                ),
                SkillMeta(
                    id="review",
                    name="Review",
                    path=path2,
                    summary="Review",
                    load_policy="free",
                    priority=80,
                    zones=["default"],
                ),
            ]
            resolved1 = _make_resolved(tmpdir, skills1)
            lock = SkillsLock(resolved1)
            lock_path = lock.write(str(tmpdir / "skills.lock.json"))

            # 删除一个 skill
            skills2 = [skills1[0]]
            resolved2 = _make_resolved(tmpdir, skills2)

            issues = SkillsLock.check(resolved2, lock_path)
            assert len(issues) == 1
            assert "已删除" in issues[0]

    def test_check_load_policy_changed(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            path1 = _make_skill_file(tmpdir, "tdd", "---\nid: tdd\n---\n# TDD")

            skills1 = [
                SkillMeta(
                    id="tdd",
                    name="TDD",
                    path=path1,
                    summary="TDD",
                    load_policy="free",
                    priority=90,
                    zones=["default"],
                ),
            ]
            resolved1 = _make_resolved(tmpdir, skills1)
            lock = SkillsLock(resolved1)
            lock_path = lock.write(str(tmpdir / "skills.lock.json"))

            # load_policy 变了
            skills2 = [
                SkillMeta(
                    id="tdd",
                    name="TDD",
                    path=path1,
                    summary="TDD",
                    load_policy="require",
                    priority=90,
                    zones=["default"],
                ),
            ]
            resolved2 = _make_resolved(tmpdir, skills2)

            issues = SkillsLock.check(resolved2, lock_path)
            assert len(issues) == 1
            assert "load_policy 变化" in issues[0]
