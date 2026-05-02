"""SyncTarget 抽象基类 + 内置实现

设计原则：
- write(skill_id, content, meta) 支持聚合型和分散型两种 target
- 聚合型（如 AGENTS.md）：write 追加内容到内存缓冲区，finalize 一次性写文件
- 分散型（如 Hermes）：write 直接写单个文件
- sync 语义默认与 build 一致：forced 完整内容 + passive 摘要，按 Zone 过滤
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from skills_orchestrator.models import ResolvedConfig, SkillMeta
from skills_orchestrator.compiler.content_resolver import SkillContentResolver


# ═══════════════════════════ 抽象基类 ═══════════════════════════


class SyncTarget(ABC):
    """同步目标抽象基类"""

    @property
    @abstractmethod
    def name(self) -> str:
        """目标名称（用于日志）"""

    @abstractmethod
    def write(self, skill_id: str, content: str, meta: Dict[str, Any]) -> None:
        """写入一个 skill 的内容

        Args:
            skill_id: skill 唯一标识
            content: skill 完整 markdown 内容（含 frontmatter）
            meta: 元数据字典，至少包含 name, summary, tags, load_policy 等
        """

    @abstractmethod
    def finalize(self) -> int:
        """完成写入，返回写入的 skill 数量"""

    def prepare(self) -> None:
        """可选的预处理步骤（创建目录等）"""
        pass


# ═══════════════════════════ HermesTarget ═══════════════════════════


class HermesTarget(SyncTarget):
    """Hermes skill 目录同步

    格式：~/.hermes/skills/{category}/{skill_id}/SKILL.md
    - 每个 skill 一个子目录，内含 SKILL.md
    - SKILL.md 带 YAML frontmatter（与 skills-orchestrator 格式一致）
    - category 从 skill 的 tags 推断，或默认 "general"
    """

    # tag → category 映射表（可扩展）
    TAG_CATEGORY_MAP: Dict[str, str] = {
        "coding": "software-development",
        "code": "software-development",
        "quality": "software-development",
        "testing": "software-development",
        "tdd": "software-development",
        "refactor": "software-development",
        "debug": "software-development",
        "error": "software-development",
        "style": "software-development",
        "naming": "software-development",
        "readability": "software-development",
        "api": "software-development",
        "design": "software-development",
        "rest": "software-development",
        "git": "software-development",
        "workflow": "software-development",
        "parallel": "software-development",
        "review": "software-development",
        "security": "software-development",
        "owasp": "software-development",
        "ops": "devops",
        "deployment": "devops",
        "checklist": "devops",
        "production": "devops",
        "environment": "devops",
        "config": "devops",
        "planning": "productivity",
        "estimation": "productivity",
        "project": "productivity",
        "process": "productivity",
        "brainstorming": "productivity",
        "decision": "productivity",
        "docs": "productivity",
        "readme": "productivity",
        "mindset": "software-development",
        "best-practices": "software-development",
        "performance": "software-development",
        "profiling": "software-development",
        "optimization": "software-development",
        "reliability": "software-development",
        "pr": "software-development",
        "base": "software-development",
        "english": "software-development",
    }

    def __init__(self, base_dir: Optional[str] = None, category_override: Optional[str] = None):
        """
        Args:
            base_dir: Hermes skills 根目录，默认 ~/.hermes/skills
            category_override: 强制所有 skill 使用同一 category
        """
        self.base_dir = Path(base_dir or os.path.expanduser("~/.hermes/skills"))
        self.category_override = category_override
        self._count = 0

    @property
    def name(self) -> str:
        return f"Hermes ({self.base_dir})"

    def prepare(self) -> None:
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _infer_category(self, meta: Dict[str, Any]) -> str:
        """从 skill tags 推断 category"""
        if self.category_override:
            return self.category_override

        tags = meta.get("tags", [])
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(",") if t.strip()]

        for tag in tags:
            tag_lower = tag.lower()
            if tag_lower in self.TAG_CATEGORY_MAP:
                return self.TAG_CATEGORY_MAP[tag_lower]

        return "general"

    def write(self, skill_id: str, content: str, meta: Dict[str, Any]) -> None:
        category = self._infer_category(meta)
        skill_dir = self.base_dir / category / skill_id
        skill_dir.mkdir(parents=True, exist_ok=True)

        skill_file = skill_dir / "SKILL.md"

        # 确保 content 有 frontmatter
        if not content.startswith("---"):
            frontmatter = {
                "name": meta.get("name", skill_id),
                "description": meta.get("summary", ""),
                "version": meta.get("version", "1.0.0"),
                "metadata": {
                    "hermes": {
                        "tags": meta.get("tags", []),
                        "source": "skills-orchestrator",
                        "load_policy": meta.get("load_policy", "free"),
                        "priority": meta.get("priority", 50),
                    }
                },
            }
            fm_yaml = yaml.dump(
                frontmatter, allow_unicode=True, default_flow_style=False, sort_keys=False
            )
            content = f"---\n{fm_yaml}---\n\n{content}"

        skill_file.write_text(content, encoding="utf-8")
        self._count += 1

    def finalize(self) -> int:
        return self._count


# ═══════════════════════════ OpenClawTarget ═══════════════════════════


class OpenClawTarget(SyncTarget):
    """OpenClaw skill 目录同步

    格式（已确认，与 Hermes 相同的目录结构）：
    - 目录：~/.openclaw/workspace/skills/{skill_id}/SKILL.md
    - 每个 skill 一个子目录，内含 SKILL.md
    - SKILL.md 带 YAML frontmatter，必须包含 name 和 description 字段
    - OpenClaw 扫描逻辑：递归扫描 skills 根目录下的子目录，找 SKILL.md

    两个 skill 根目录：
    1. workspace skills: ~/.openclaw/workspace/skills/ （用户自定义，sync 写这里）
    2. bundled skills: /opt/homebrew/lib/node_modules/openclaw/skills/ （内置，只读）

    注意：OpenClaw 没有额外的注册步骤，只要文件放在 skills 目录下就会被自动发现。
    """

    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = Path(base_dir or os.path.expanduser("~/.openclaw/workspace/skills"))
        self._count = 0

    @property
    def name(self) -> str:
        return f"OpenClaw ({self.base_dir})"

    def prepare(self) -> None:
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def write(self, skill_id: str, content: str, meta: Dict[str, Any]) -> None:
        skill_dir = self.base_dir / skill_id
        skill_dir.mkdir(parents=True, exist_ok=True)

        skill_file = skill_dir / "SKILL.md"

        # 确保 content 有 frontmatter 且包含 name + description
        # OpenClaw 要求 frontmatter 中至少有 name 和 description
        if content.startswith("---"):
            # 已有 frontmatter，检查是否包含必要字段
            end = content.find("\n---", 3)
            if end != -1:
                fm_text = content[3:end].strip()
                fm = yaml.safe_load(fm_text) or {}
                if not isinstance(fm, dict):
                    fm = {}
                needs_patch = False
                if not fm.get("name") and meta.get("name"):
                    fm["name"] = meta["name"]
                    needs_patch = True
                if not fm.get("description") and meta.get("summary"):
                    fm["description"] = meta["summary"]
                    needs_patch = True
                if needs_patch:
                    new_fm = yaml.dump(
                        fm, allow_unicode=True, default_flow_style=False, sort_keys=False
                    )
                    body = content[end + 4 :].lstrip("\n")
                    content = f"---\n{new_fm}---\n\n{body}"
        else:
            # 没有 frontmatter，补全 OpenClaw 要求的最小格式
            frontmatter = {
                "name": meta.get("name", skill_id),
                "description": meta.get("summary", ""),
            }
            if meta.get("tags"):
                frontmatter["tags"] = meta["tags"]
            fm_yaml = yaml.dump(
                frontmatter, allow_unicode=True, default_flow_style=False, sort_keys=False
            )
            content = f"---\n{fm_yaml}---\n\n{content}"

        skill_file.write_text(content, encoding="utf-8")
        self._count += 1

    def finalize(self) -> int:
        return self._count


# ═══════════════════════════ CopilotTarget ═══════════════════════════


class CopilotTarget(SyncTarget):
    """GitHub Copilot 指令同步

    格式：项目根目录下 .github/copilot-instructions.md
    - 聚合型：所有 skill 合并写入一个文件
    - 格式与 AGENTS.md 相同（纯 markdown，带 frontmatter 块）
    - GitHub Copilot 自动读取此文件作为项目级指令
    """

    def __init__(self, output_path: str = ".github/copilot-instructions.md"):
        self.output_path = Path(output_path)
        self._parts: List[str] = []
        self._count = 0

    @property
    def name(self) -> str:
        return f"Copilot ({self.output_path})"

    def prepare(self) -> None:
        self.output_path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, skill_id: str, content: str, meta: Dict[str, Any]) -> None:
        stripped = content.strip()
        if stripped.startswith("---"):
            self._parts.append(stripped)
        else:
            self._parts.append(f"---\n{stripped}\n---")
        self._count += 1

    def finalize(self) -> int:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        header = f"<!-- Generated by Skills Orchestrator sync | {timestamp} -->\n\n"
        body = "\n\n".join(self._parts)
        self.output_path.write_text(header + body, encoding="utf-8")
        return self._count


# ═══════════════════════════ AGENTS.md Target ═══════════════════════════


class AgentsMdTarget(SyncTarget):
    """聚合型 Target — 把所有 skill 写进一个 AGENTS.md

    聚合型策略：
    - write 时追加到内存缓冲区，区分 forced / passive
    - finalize 时生成与 build 一致的分区格式（Required Skills + Available Skills 表格）
    """

    def __init__(self, output_path: str = "AGENTS.md"):
        self.output_path = Path(output_path)
        self._forced_parts: List[str] = []
        self._passive_parts: List[str] = []  # --full 模式下 passive 的完整内容
        self._passive_rows: List[str] = []  # 表格行: "| name | summary | tags |"
        self._forced_count = 0
        self._passive_count = 0

    @property
    def name(self) -> str:
        return f"AGENTS.md ({self.output_path})"

    def write(self, skill_id: str, content: str, meta: Dict[str, Any]) -> None:
        is_summary = meta.get("_is_summary", False)
        load_policy = meta.get("load_policy", "free")

        # 判断是否为 required (require) skill
        is_required = load_policy == "require"

        if is_summary:
            # passive 摘要模式：只生成表格行
            name = meta.get("name", skill_id)
            summary = meta.get("summary", "")
            tags = ", ".join(meta.get("tags", []))
            self._passive_rows.append(f"| {name} | {summary} | {tags} |")
            self._passive_count += 1
        elif is_required:
            # required skill 完整内容 → Required Skills 区
            stripped = content.strip()
            if stripped.startswith("---"):
                self._forced_parts.append(stripped)
            else:
                self._forced_parts.append(f"---\n{stripped}\n---")
            self._forced_count += 1
        else:
            # passive skill 完整内容（--full 模式）→ Available Skills 区
            # 先生成表格行
            name = meta.get("name", skill_id)
            summary = meta.get("summary", "")
            tags = ", ".join(meta.get("tags", []))
            self._passive_rows.append(f"| {name} | {summary} | {tags} |")
            # 完整内容追加到被动区
            stripped = content.strip()
            if stripped.startswith("---"):
                self._passive_parts.append(stripped)
            else:
                self._passive_parts.append(f"---\n{stripped}\n---")
            self._passive_count += 1

    def finalize(self) -> int:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        lines = [
            f"<!-- Generated by Skills Orchestrator sync | {timestamp} -->",
            "",
            "## Required Skills",
            "",
            "> 以下 skills 为强制加载，所有任务均须遵循。",
            "",
        ]

        # Required Skills 区
        if self._forced_parts:
            lines.append("\n\n".join(self._forced_parts))
        else:
            lines.append("> 当前无强制 skills。")

        lines.append("")
        lines.append("## Available Skills")
        lines.append("")
        lines.append("> 以下 skills 按需选用。根据当前任务选择最相关的 skill 加载。")
        lines.append("")
        lines.append("| Skill | 说明 | Tags |")
        lines.append("|-------|------|------|")

        # Available Skills 区
        if self._passive_rows:
            lines.extend(self._passive_rows)
        else:
            lines.append("> 当前无可选 skills。")

        # --full 模式下 passive skill 的完整内容
        if self._passive_parts:
            lines.append("")
            lines.append("### 完整内容")
            lines.append("")
            lines.append("\n\n".join(self._passive_parts))

        lines.append("")
        lines.append('如需使用某个 skill，请说明"使用 [skill-name] skill"，系统将加载完整内容。')

        self.output_path.write_text("\n".join(lines), encoding="utf-8")
        return self._forced_count + self._passive_count


# ═══════════════════════════ Sync Engine ═══════════════════════════


class SyncEngine:
    """同步引擎 — 根据 ResolvedConfig 将 skills 导出到 target

    语义：
    - 默认模式（与 build 一致）：forced 完整内容 + passive 摘要，按 Zone 过滤
    - --full 模式：所有 skill 完整内容（不分 forced/passive），不按 Zone 过滤
    """

    def __init__(
        self, resolved: ResolvedConfig, full: bool = False, registry=None, all_skills=None
    ):
        """
        Args:
            resolved: 编译解析后的配置
            full: True = 全量导出所有 skill 完整内容
            registry: SkillRegistry 实例（可选），传入后走 registry.get_content()
                     以支持 base 继承合并
            all_skills: 全量 skill 列表（用于跨 Zone base 继承）
        """
        self.resolved = resolved
        self.full = full
        current_skills = resolved.forced_skills + resolved.passive_skills
        self._resolver = SkillContentResolver(
            base_dir=resolved.base_dir,
            registry=registry,
            skills=current_skills,
            all_skills=all_skills or current_skills,
        )

    def _read_skill_content(self, skill: SkillMeta) -> str:
        """读取 skill 文件完整内容（通过 SkillContentResolver 统一处理 base 继承合并）。"""
        return self._resolver.read(skill)

    def _make_meta(self, skill: SkillMeta, effective_load_policy: str | None = None) -> dict:
        """生成 skill 元数据，支持覆盖 load_policy

        Args:
            skill: skill 元数据
            effective_load_policy: 覆盖的 load_policy（如 Zone require 升级后的 "require"）
        """
        return {
            "name": skill.name,
            "summary": skill.summary,
            "tags": skill.tags,
            "load_policy": effective_load_policy or skill.load_policy,
            "priority": skill.priority,
        }

    def _make_summary_content(
        self, skill: SkillMeta, effective_load_policy: str | None = None
    ) -> str:
        """为 passive skill 生成摘要格式的 markdown

        Args:
            skill: skill 元数据
            effective_load_policy: 覆盖的 load_policy
        """
        tags = ", ".join(skill.tags)
        load_policy = effective_load_policy or skill.load_policy
        return (
            f"---\n"
            f"id: {skill.id}\n"
            f"name: {skill.name}\n"
            f'summary: "{skill.summary}"\n'
            f"tags: [{tags}]\n"
            f"load_policy: {load_policy}\n"
            f"---\n\n"
            f"# {skill.name}\n\n"
            f"{skill.summary}\n\n"
            f"> 如需完整内容，请使用 `skills-orchestrator sync --full` 导出"
        )

    def sync_to(self, target: SyncTarget) -> int:
        """将 skills 同步到指定 target

        Returns:
            写入的 skill 数量
        """
        target.prepare()

        if self.full:
            # --full 模式：所有 skill 完整内容
            all_skills = list(self.resolved.forced_skills) + list(self.resolved.passive_skills)
            for skill in all_skills:
                content = self._read_skill_content(skill)
                # forced skills 使用 "require"，passive 使用原始值
                effective_policy = "require" if skill in self.resolved.forced_skills else None
                target.write(skill.id, content, self._make_meta(skill, effective_policy))
        else:
            # 默认模式：forced 完整 + passive 摘要，按 Zone
            for skill in self.resolved.forced_skills:
                content = self._read_skill_content(skill)
                target.write(skill.id, content, self._make_meta(skill, "require"))

            for skill in self.resolved.passive_skills:
                content = self._make_summary_content(skill)
                meta = {**self._make_meta(skill), "_is_summary": True}
                target.write(skill.id, content, meta)

        return target.finalize()


# ═══════════════════════════ Cursor Target ═══════════════════════════


class CursorTarget(SyncTarget):
    """Cursor rules 同步

    格式：项目根目录下 .cursor/rules/*.mdc
    - 分散型：每个 skill 对应一个文件
    - .mdc 格式支持 YAML frontmatter
    - Cursor 自动扫描 .cursor/rules/ 目录下的 .mdc 文件
    """

    def __init__(self, output_dir: str = "."):
        self.output_dir = Path(output_dir)
        self.rules_dir = self.output_dir / ".cursor" / "rules"
        self._count = 0

    @property
    def name(self) -> str:
        return f"Cursor ({self.rules_dir})"

    def prepare(self) -> None:
        """创建 .cursor/rules/ 目录"""
        self.rules_dir.mkdir(parents=True, exist_ok=True)

    def write(self, skill_id: str, content: str, meta: Dict[str, Any]) -> None:
        """写入单个 skill 文件"""
        rule_file = self.rules_dir / f"{skill_id}.mdc"

        # 确保 content 有 frontmatter
        if not content.startswith("---"):
            # 没有 frontmatter，添加最基本的描述
            frontmatter = {
                "name": meta.get("name", skill_id),
            }
            if meta.get("summary"):
                frontmatter["description"] = meta["summary"]
            fm_yaml = yaml.dump(
                frontmatter, allow_unicode=True, default_flow_style=False, sort_keys=False
            )
            content = f"---\n{fm_yaml}---\n\n{content}"

        rule_file.write_text(content, encoding="utf-8")
        self._count += 1

    def finalize(self) -> int:
        """返回写入的文件数量"""
        return self._count


# ═══════════════════════════ Target Registry ═══════════════════════════


TARGET_REGISTRY: Dict[str, type] = {
    "hermes": HermesTarget,
    "openclaw": OpenClawTarget,
    "copilot": CopilotTarget,
    "agents-md": AgentsMdTarget,
    "cursor": CursorTarget,
}


def get_target(name: str, **kwargs: Any) -> SyncTarget:
    """根据名称创建 SyncTarget 实例"""
    cls = TARGET_REGISTRY.get(name)
    if cls is None:
        available = ", ".join(TARGET_REGISTRY.keys())
        raise ValueError(f"未知的同步目标: {name}（可用: {available}）")
    return cls(**kwargs)
