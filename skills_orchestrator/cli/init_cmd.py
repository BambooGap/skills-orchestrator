"""init command — 从本地 skills 目录生成 skills.yaml"""

from __future__ import annotations

from pathlib import Path

import click
import yaml

from skills_orchestrator.security import console_safe_symbol, console_safe_text

from .helpers import _ok, _warn, _parse_frontmatter


# ─── CLI command ────────────────────────────────────────────


@click.command()
@click.option("--skills-dir", "-d", default="./skills", help="Skills 目录")
@click.option("--output", "-o", default="skills.yaml", help="输出配置文件路径")
@click.option(
    "--non-interactive",
    "-y",
    is_flag=True,
    help="非交互模式：直接从 frontmatter 生成配置，不逐一询问",
)
def init(skills_dir: str, output: str, non_interactive: bool):
    """初始化，从本地 skills 目录生成 skills.yaml

    默认为交互式模式（逐一询问每个 skill 的配置）。
    使用 --non-interactive 可直接从 frontmatter 自动生成配置，
    仅对缺少 frontmatter 的字段使用默认值。
    """
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

    output_path = Path(output)
    with open(output_path, "w", encoding="utf-8") as f:
        yaml.dump(config, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

    click.echo("")
    click.echo(_ok(f"生成 {output_path}，包含 {len(entries)} 个 skills"))
    if non_interactive and missing_fm_count > 0:
        click.echo(_warn(f"其中 {missing_fm_count} 个文件缺少 frontmatter，使用了推断默认值"))
    click.echo("\n下一步：")
    click.echo(f"  export SKILLS_ROOT={skills_path.resolve()}")
    click.echo(f"  skills-orchestrator build --config {output_path}")
