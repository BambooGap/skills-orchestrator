"""skills.lock — 保证 Skill 加载的可复现性

build 时生成 skills.lock，记录每个 skill 的：
- 文件内容 hash（SHA-256）
- frontmatter 中的 load_policy / priority / zones
- base 继承关系

validate 时检查 lock 是否过期，防止 Skill 更新导致行为变化。
"""

import hashlib
import json
from datetime import datetime
from pathlib import Path

from skills_orchestrator.models import ResolvedConfig


class LockEntry:
    """单个 skill 的 lock 记录"""

    __slots__ = (
        "id",
        "name",
        "path",
        "content_hash",
        "source_load_policy",
        "effective_load_policy",
        "priority",
        "zones",
        "base",
    )

    def __init__(
        self,
        id: str,
        name: str,
        path: str,
        content_hash: str,
        source_load_policy: str,
        effective_load_policy: str,
        priority: int,
        zones: list[str],
        base: str = "",
    ):
        self.id = id
        self.name = name
        self.path = path
        self.content_hash = content_hash
        self.source_load_policy = source_load_policy
        self.effective_load_policy = effective_load_policy
        self.priority = priority
        self.zones = zones
        self.base = base

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "path": self.path,
            "content_hash": self.content_hash,
            "source_load_policy": self.source_load_policy,
            "effective_load_policy": self.effective_load_policy,
            "priority": self.priority,
            "zones": self.zones,
            "base": self.base,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "LockEntry":
        return cls(**d)


class SkillsLock:
    """skills.lock 文件管理"""

    def __init__(self, resolved: ResolvedConfig, base_dir: str = ""):
        self.resolved = resolved
        self.base_dir = base_dir or resolved.base_dir

    @staticmethod
    def _hash_file(path: Path) -> str:
        """计算文件 SHA-256 hash"""
        if not path.exists():
            return ""
        return hashlib.sha256(path.read_bytes()).hexdigest()[:16]

    def _resolve_path(self, skill_path: str) -> Path:
        p = Path(skill_path)
        if p.is_absolute():
            return p
        return (Path(self.base_dir) / p).resolve()

    def generate(self) -> dict:
        """生成 lock 内容"""
        entries = []
        all_skills = self.resolved.forced_skills + self.resolved.passive_skills

        # 计算 effective_load_policy
        zone = self.resolved.active_zone
        zone_forces_all = zone is not None and zone.load_policy == "require"

        def effective_policy(skill) -> str:
            if skill.load_policy == "require":
                return "require"
            if zone_forces_all and skill.load_policy == "free":
                return "require"
            return skill.load_policy

        for skill in all_skills:
            path = self._resolve_path(skill.path)
            content_hash = self._hash_file(path)
            entries.append(
                LockEntry(
                    id=skill.id,
                    name=skill.name,
                    path=skill.path,
                    content_hash=content_hash,
                    source_load_policy=skill.load_policy,
                    effective_load_policy=effective_policy(skill),
                    priority=skill.priority,
                    zones=skill.zones,
                    base=skill.base,
                ).to_dict()
            )

        # blocked skills 也记录（用于检测冲突变化）
        for skill in self.resolved.blocked_skills:
            path = self._resolve_path(skill.path)
            content_hash = self._hash_file(path)
            entries.append(
                LockEntry(
                    id=skill.id,
                    name=skill.name,
                    path=skill.path,
                    content_hash=content_hash,
                    source_load_policy=skill.load_policy,
                    effective_load_policy=effective_policy(skill),
                    priority=skill.priority,
                    zones=skill.zones,
                    base=skill.base,
                ).to_dict()
            )

        return {
            "version": "1.1",
            "generated_at": datetime.now().isoformat(),
            "zone": self.resolved.active_zone.id if self.resolved.active_zone else "default",
            "skills": entries,
        }

    def write(self, output_path: str = "skills.lock.json") -> str:
        """写入 lock 文件，返回文件路径"""
        data = self.generate()
        path = Path(output_path)
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return str(path)

    @staticmethod
    def load(lock_path: str) -> dict:
        """加载 lock 文件"""
        return json.loads(Path(lock_path).read_text(encoding="utf-8"))

    @staticmethod
    def check(resolved: ResolvedConfig, lock_path: str, base_dir: str = "") -> list[str]:
        """检查当前 skill 状态是否与 lock 一致，返回差异列表"""
        lock_data = SkillsLock.load(lock_path)
        lock_entries = {e["id"]: e for e in lock_data.get("skills", [])}
        issues = []
        _base_dir = base_dir or resolved.base_dir

        all_skills = resolved.forced_skills + resolved.passive_skills + resolved.blocked_skills

        # 计算 effective_load_policy
        zone = resolved.active_zone
        zone_forces_all = zone is not None and zone.load_policy == "require"

        def effective_policy(skill) -> str:
            if skill.load_policy == "require":
                return "require"
            if zone_forces_all and skill.load_policy == "free":
                return "require"
            return skill.load_policy

        for skill in all_skills:
            entry = lock_entries.get(skill.id)
            if not entry:
                issues.append(f"+ {skill.id}: 新增 skill（lock 中不存在）")
                continue

            # 检查 content hash
            p = Path(skill.path)
            if not p.is_absolute():
                p = (Path(_base_dir) / p).resolve()
            current_hash = SkillsLock._hash_file(p)
            if current_hash != entry.get("content_hash", ""):
                issues.append(
                    f"~ {skill.id}: 内容已变化（hash {entry['content_hash']} → {current_hash}）"
                )

            # 检查 source_load_policy 变化（兼容旧版 lock）
            old_policy = entry.get("source_load_policy") or entry.get("load_policy")
            if skill.load_policy != old_policy:
                issues.append(
                    f"~ {skill.id}: load_policy 变化"
                    f"（{old_policy} → {skill.load_policy}）"
                )

            # 检查 effective_load_policy 变化（仅当 lock 版本 >= 1.1）
            if lock_data.get("version") >= "1.1":
                old_effective = entry.get("effective_load_policy")
                current_effective = effective_policy(skill)
                if current_effective != old_effective:
                    issues.append(
                        f"~ {skill.id}: effective_load_policy 变化"
                        f"（{old_effective} → {current_effective}）"
                    )

            # 检查 priority 变化
            if skill.priority != entry.get("priority"):
                issues.append(
                    f"~ {skill.id}: priority 变化（{entry.get('priority')} → {skill.priority}）"
                )

        # 检查 lock 中有但当前没有的 skill（被删除）
        current_ids = {s.id for s in all_skills}
        for skill_id in lock_entries:
            if skill_id not in current_ids:
                issues.append(f"- {skill_id}: skill 已删除（lock 中存在）")

        return issues
