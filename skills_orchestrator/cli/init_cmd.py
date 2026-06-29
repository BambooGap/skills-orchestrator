"""init command — 从本地 skills 目录生成 skills.yaml"""

from __future__ import annotations

import os
from datetime import date, timedelta
from pathlib import Path

import click
import yaml

from skills_orchestrator import __version__
from skills_orchestrator.security import console_safe_symbol, console_safe_text

from .helpers import _ok, _warn, _parse_frontmatter


# ─── CLI command ────────────────────────────────────────────


@click.command()
@click.option("--skills-dir", "-d", default="./skills", help="Skills 目录")
@click.option("--output", "-o", default=None, help="输出配置文件路径")
@click.option(
    "--non-interactive",
    "-y",
    is_flag=True,
    help="非交互模式：直接从 frontmatter 生成配置，不逐一询问",
)
@click.option(
    "--template",
    type=click.Choice(["team-standard"]),
    default=None,
    help="生成团队标准化 starter kit，而不是扫描现有 skills 目录",
)
@click.option(
    "--hardened-workflow",
    is_flag=True,
    help="template 模式生成供应链更严格的 pinned GitHub Actions workflow",
)
@click.option("--force", is_flag=True, help="覆盖 template 已存在的目标文件")
def init(
    skills_dir: str,
    output: str | None,
    non_interactive: bool,
    template: str | None,
    hardened_workflow: bool,
    force: bool,
):
    """初始化，从本地 skills 目录生成 skills.yaml

    默认为交互式模式（逐一询问每个 skill 的配置）。
    使用 --non-interactive 可直接从 frontmatter 自动生成配置，
    仅对缺少 frontmatter 的字段使用默认值。
    """
    if template == "team-standard":
        _init_team_standard(output=output, force=force, hardened_workflow=hardened_workflow)
        return

    skills_path = Path(skills_dir)

    if not skills_path.exists():
        if non_interactive or click.confirm(f"目录 {skills_dir} 不存在，是否创建？", default=True):
            skills_path.mkdir(parents=True)
            click.echo(_ok(f"已创建目录: {skills_path}"))
        else:
            click.echo("已取消")
            return

    # 扫描 skill 文件：顶层 *.md + 子目录中的 SKILL.md
    md_files = sorted(skills_path.glob("*.md"))
    for sub_skill in sorted(skills_path.rglob("*.md")):
        if sub_skill not in md_files:
            md_files.append(sub_skill)
    skip_names = {"README.md", "CLAUDE.md", "CURSOR.md", "EXAMPLES.md"}
    md_files = [f for f in md_files if f.name not in skip_names and not f.name.startswith(".")]
    if not md_files:
        click.echo(_warn(f"{skills_dir} 中没有 .md 文件，请先添加 skill 文件"))
        return

    click.echo(
        f"\n找到 {len(md_files)} 个 skill 文件"
        + ("，非交互模式：直接从 frontmatter 生成" if non_interactive else "，开始配置：")
        + "\n"
    )

    entries = []
    missing_fm_count = 0
    for md_file in md_files:
        content = md_file.read_text(encoding="utf-8")
        meta = _parse_frontmatter(content)
        has_frontmatter = bool(meta.get("id") or meta.get("name"))

        skill_id = meta.get("id", md_file.stem)
        default_name = meta.get("name", md_file.stem.replace("-", " ").title())
        default_summary = meta.get("summary", "")
        default_tags = ", ".join(meta.get("tags", []))
        default_policy = meta.get("load_policy", "free")
        default_priority = meta.get("priority", 50)

        if not has_frontmatter:
            missing_fm_count += 1

        if non_interactive:
            name = default_name
            summary = default_summary
            tags_list = (
                [t.strip() for t in default_tags.split(",") if t.strip()]
                if isinstance(default_tags, str)
                else default_tags
            )
            policy = default_policy
            priority = default_priority
            click.echo(
                console_safe_text(
                    f"  {md_file.name} {console_safe_symbol('→', '->')} "
                    f"{skill_id} ({policy}, p{priority})"
                )
            )
        else:
            sep = console_safe_symbol("─", "-") * 3
            click.echo(console_safe_text(click.style(f"{sep} {md_file.name} {sep}", bold=True)))
            name = click.prompt("  名称", default=default_name)
            summary = click.prompt("  简介", default=default_summary)
            tags_str = click.prompt("  标签（逗号分隔）", default=default_tags)
            policy = click.prompt(
                "  加载策略",
                default=default_policy,
                type=click.Choice(["require", "free"]),
                show_choices=True,
            )
            priority = click.prompt("  优先级 (0-999)", default=default_priority, type=int)
            tags_list = [t.strip() for t in tags_str.split(",") if t.strip()]
            click.echo("")

        entries.append(
            {
                "id": skill_id,
                "name": name,
                "path": f"${{SKILLS_ROOT}}/{md_file.relative_to(skills_path)}",
                "summary": summary,
                "tags": tags_list
                if isinstance(tags_list, list)
                else [t.strip() for t in default_tags.split(",") if t.strip()],
                "load_policy": policy,
                "priority": priority,
                "zones": meta.get("zones", ["default"]),
                "conflict_with": meta.get("conflict_with", []),
                "base": meta.get("base", ""),
                "owner": meta.get("owner", ""),
                "source": meta.get("source", ""),
                "version": meta.get("version", ""),
                "lifecycle": meta.get("lifecycle", "active"),
                "approvers": _coerce_list(meta.get("approvers", [])),
                "reviewed_at": meta.get("reviewed_at", ""),
                "expires_at": meta.get("expires_at", ""),
                "license": meta.get("license", ""),
                "provenance": meta.get("provenance", {}),
            }
        )

    config = {
        "version": "1.0",
        "zones": [
            {
                "id": "default",
                "name": "默认区",
                "load_policy": "free",
                "priority": 0,
                "rules": [],
            }
        ],
        "skills": entries,
        "combos": [],
    }

    output_path = Path(output or "skills.yaml")
    with open(output_path, "w", encoding="utf-8") as f:
        yaml.dump(config, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

    click.echo("")
    click.echo(_ok(f"生成 {output_path}，包含 {len(entries)} 个 skills"))
    if non_interactive and missing_fm_count > 0:
        click.echo(_warn(f"其中 {missing_fm_count} 个文件缺少 frontmatter，使用了推断默认值"))
    click.echo("\n下一步：")
    click.echo(f"  export SKILLS_ROOT={skills_path.resolve()}")
    click.echo(f"  skills-orchestrator build --config {output_path}")


def _init_team_standard(*, output: str | None, force: bool, hardened_workflow: bool) -> None:
    """Generate a team-standard starter kit using the existing init entrypoint."""
    project_root = Path.cwd().resolve()
    config_path = _template_config_path(output, project_root)
    skills_dir = project_root / "skills"
    team_skills_dir = skills_dir / "team"
    workflows_dir = project_root / ".github" / "workflows"
    evidence_dir = project_root / "evidence"
    pipelines_dir = config_path.parent / "pipelines"

    targets = {
        config_path: _team_standard_config(config_path, skills_dir),
        team_skills_dir / "engineering-standards.md": _team_engineering_standards_skill(),
        team_skills_dir / "code-review.md": _team_code_review_skill(),
        team_skills_dir / "release-checklist.md": _team_release_checklist_skill(),
        pipelines_dir / "team-review.yaml": _team_review_pipeline(),
        workflows_dir / "skills-orchestrator.yml": _team_standard_workflow(
            hardened=hardened_workflow
        ),
        evidence_dir / ".gitkeep": "",
    }

    for path in targets:
        _reject_symlink_target(path, project_root)
        if path.exists() and not force:
            raise click.ClickException(f"目标文件已存在，未覆盖: {path}（如需覆盖请加 --force）")

    for path, content in targets.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    click.echo(_ok("生成 team-standard starter kit"))
    click.echo(f"  config: {config_path}")
    click.echo(f"  skills: {team_skills_dir}")
    click.echo(f"  pipeline: {pipelines_dir / 'team-review.yaml'}")
    click.echo(f"  workflow: {workflows_dir / 'skills-orchestrator.yml'}")
    click.echo(f"  evidence: {evidence_dir}")
    click.echo("\n下一步：")
    click.echo(
        f"  skills-orchestrator check --config {config_path} --policy-pack builtin/team-standard"
    )
    click.echo(f"  skills-orchestrator build --config {config_path} --lock")
    click.echo(
        f"  skills-orchestrator doctor --config {config_path} --profile adopter --fail-under 100"
    )
    click.echo(
        "  note: run build --lock before expecting doctor 100/100; it creates AGENTS.md "
        "and skills.lock.json."
    )


def _team_standard_config(config_path: Path, skills_dir: Path) -> str:
    relative_skills_dir = Path(
        os.path.relpath(skills_dir, config_path.parent or Path("."))
    ).as_posix()
    config = {
        "version": "2.0",
        "skill_dirs": [relative_skills_dir],
        "zones": [
            {
                "id": "default",
                "name": "Default",
                "load_policy": "free",
                "priority": 0,
                "rules": [],
            }
        ],
        "overrides": [],
        "combos": [
            {
                "id": "team-review",
                "name": "Team Review",
                "skills": ["team-code-review", "team-release-checklist"],
                "description": "Run code review and release readiness checks together.",
            }
        ],
    }
    return yaml.dump(config, allow_unicode=True, default_flow_style=False, sort_keys=False)


def _team_engineering_standards_skill() -> str:
    reviewed_at, expires_at = _default_review_window()
    return f"""---
id: team-engineering-standards
name: Team Engineering Standards
summary: Shared engineering standards for agent-assisted work in this repository.
tags: [team-standard, engineering, agent]
load_policy: free
priority: 70
zones: [default]
owner: agent-platform
source: repo://skills/team/engineering-standards.md
version: 1.0.0
lifecycle: active
reviewed_at: {reviewed_at}
expires_at: {expires_at}
license: MIT
---

# Team Engineering Standards

Use repo-local commands, keep changes scoped, and update tests and docs with behavior changes.
Record skipped verification with the exact command and reason.
"""


def _team_code_review_skill() -> str:
    reviewed_at, expires_at = _default_review_window()
    return f"""---
id: team-code-review
name: Team Code Review
summary: Required code review checklist for changes made by agents or humans.
tags: [team-standard, review, quality]
load_policy: require
priority: 100
zones: [default]
owner: agent-platform
source: repo://skills/team/code-review.md
version: 1.0.0
lifecycle: active
approvers: [agent-platform]
reviewed_at: {reviewed_at}
expires_at: {expires_at}
license: MIT
---

# Team Code Review

Review diffs for behavioral regressions, missing tests, unsafe file operations, and stale docs.
Findings must include file paths, impact, and a concrete fix direction.
"""


def _team_release_checklist_skill() -> str:
    reviewed_at, expires_at = _default_review_window()
    return f"""---
id: team-release-checklist
name: Team Release Checklist
summary: Required release readiness checks for SkillOps-controlled repositories.
tags: [team-standard, release, ci]
load_policy: require
priority: 90
zones: [default]
owner: release-owner
source: repo://skills/team/release-checklist.md
version: 1.0.0
lifecycle: active
approvers: [release-owner]
reviewed_at: {reviewed_at}
expires_at: {expires_at}
license: MIT
---

# Team Release Checklist

Before release, verify policy checks, schema validation, registry diff review, and rollback notes.
Attach generated evidence files when the change affects runtime instructions.
"""


def _team_review_pipeline() -> str:
    pipeline = {
        "id": "team-review",
        "name": "Team Review",
        "steps": [
            {"id": "code-review", "skill": "team-code-review", "next": ["release-checklist"]},
            {"id": "release-checklist", "skill": "team-release-checklist"},
        ],
    }
    return yaml.dump(pipeline, allow_unicode=True, default_flow_style=False, sort_keys=False)


def _team_standard_workflow(*, hardened: bool = False) -> str:
    checkout_ref = (
        "actions/checkout@9c091bb21b7c1c1d1991bb908d89e4e9dddfe3e0 # v7.0.0"
        if hardened
        else "actions/checkout@v4"
    )
    hardening_note = (
        "\n# Generated with --hardened-workflow: third-party actions are pinned where practical.\n"
        if hardened
        else ""
    )
    return f"""name: skills-orchestrator{hardening_note}

on:
  pull_request:
  push:
    branches: [main]

permissions:
  contents: read

jobs:
  skillops:
    runs-on: ubuntu-latest
    env:
      SKILLS_ORCHESTRATOR_STATE_DIR: .skills-orchestrator
    steps:
      - uses: {checkout_ref}
      - uses: BambooGap/skills-orchestrator@v{__version__}
        with:
          config: config/skills.yaml
          policy-pack: builtin/team-standard
"""


def _template_config_path(output: str | None, project_root: Path) -> Path:
    raw_path = Path("config/skills.yaml") if output is None else Path(output)
    if raw_path.is_absolute():
        raise click.ClickException("--output 必须是当前项目内的相对路径")
    if any(part == ".." for part in raw_path.parts):
        raise click.ClickException("--output 不允许包含 '..'")
    resolved = (project_root / raw_path).resolve()
    try:
        resolved.relative_to(project_root)
    except ValueError as exc:
        raise click.ClickException("--output 必须位于当前项目目录内") from exc
    return resolved


def _default_review_window() -> tuple[str, str]:
    reviewed = date.today()
    return reviewed.isoformat(), (reviewed + timedelta(days=180)).isoformat()


def _reject_symlink_target(path: Path, project_root: Path) -> None:
    resolved = path.resolve()
    try:
        resolved.relative_to(project_root)
    except ValueError as exc:
        raise click.ClickException(f"目标路径逃逸当前项目目录: {path}") from exc

    cursor = project_root
    try:
        relative_parts = path.relative_to(project_root).parts
    except ValueError:
        relative_parts = path.resolve().relative_to(project_root).parts
    for part in relative_parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise click.ClickException(f"目标路径包含符号链接，未写入: {cursor}")


def _coerce_list(value) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]
