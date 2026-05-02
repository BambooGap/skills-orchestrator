#!/usr/bin/env python3
"""Skills Orchestrator CLI"""

import json
import os
import re
import urllib.request
from pathlib import Path
from typing import Optional

import click
import yaml

from .compiler import Parser, Resolver, Compressor
from .enforcer import Enforcer
from .sync.targets import get_target, SyncEngine, TARGET_REGISTRY
from .models import Manifest


# ─────────────────────────── helpers ────────────────────────────

def _ok(msg: str) -> str:
    return click.style("✓", fg="green") + f" {msg}"

def _warn(msg: str) -> str:
    return click.style("⚠", fg="yellow") + f" {msg}"

def _err(msg: str) -> str:
    return click.style("✗", fg="red") + f" {msg}"


def _parse_frontmatter(content: str) -> dict:
    """解析 YAML frontmatter（--- ... ---），返回 meta dict；无 frontmatter 时推断基本信息。"""
    if content.startswith("---"):
        end = content.find("\n---", 3)
        if end != -1:
            fm_text = content[3:end].strip()
            try:
                meta = yaml.safe_load(fm_text) or {}
                if isinstance(meta, dict):
                    # 兼容 description → summary（karpathy-skills 等仓库用 description 字段）
                    if "summary" not in meta and "description" in meta:
                        meta["summary"] = meta["description"]
                    # tags 可能是 list 或逗号分隔的字符串
                    if "tags" in meta and isinstance(meta["tags"], str):
                        meta["tags"] = [t.strip() for t in meta["tags"].split(",") if t.strip()]
                    return meta
            except yaml.YAMLError:
                pass

    # 无 frontmatter：从 markdown heading 推断
    meta = {}
    lines = content.splitlines()
    for line in lines:
        if line.startswith("# "):
            meta["name"] = line[2:].strip()
            break
    # 取第一段非空、非 heading 的文字作为 summary
    in_para = False
    para_lines = []
    for line in lines[1:]:
        if line.startswith("#"):
            if in_para:
                break
            continue
        if line.strip() == "":
            if in_para:
                break
        else:
            in_para = True
            para_lines.append(line.strip())
    if para_lines:
        summary = " ".join(para_lines)
        meta["summary"] = summary[:120] + ("..." if len(summary) > 120 else "")
    return meta


def _slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9-]", "-", text.lower()).strip("-")


def _append_skills_to_yaml(config_path: str, new_entries: list[dict]) -> None:
    """把新 skill 条目追加到现有 skills.yaml，如不存在则创建最小配置。"""
    path = Path(config_path)
    if path.exists():
        with open(path, encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}
    else:
        raw = {
            "version": "1.0",
            "zones": [{"id": "default", "name": "默认区", "load_policy": "free", "priority": 0, "rules": []}],
            "skills": [],
            "combos": [],
        }

    existing_ids = {s["id"] for s in raw.get("skills", [])}
    added = 0
    for entry in new_entries:
        if entry["id"] not in existing_ids:
            raw.setdefault("skills", []).append(entry)
            added += 1

    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(raw, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

    click.echo(_ok(f"追加 {added} 个 skill 到 {config_path}（跳过 {len(new_entries) - added} 个已存在）"))


# ─────────────────────────── GitHub import helpers ────────────────────────────

def _gh_api(api_path: str) -> object:
    """优先用 gh CLI（已认证，无限速），失败则回退到 urllib。"""
    import subprocess
    try:
        result = subprocess.run(
            ["gh", "api", api_path],
            capture_output=True, text=True, timeout=15
        )
        if result.returncode == 0:
            return json.loads(result.stdout)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # 回退：未认证的 GitHub API
    url = f"https://api.github.com/{api_path.lstrip('/')}"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "skills-orchestrator/1.0", "Accept": "application/vnd.github.v3+json"},
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())


def _fetch_raw(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "skills-orchestrator/1.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.read().decode("utf-8")


def _github_url_to_parts(source: str) -> tuple[str, str, str, str]:
    """解析 GitHub URL，返回 (owner, repo, ref, path)。"""
    m = re.match(
        r"https?://github\.com/([^/]+)/([^/]+)(?:/(tree|blob)/([^/]+)(/.*)?)?",
        source.rstrip("/"),
    )
    if not m:
        raise ValueError(f"无法解析 GitHub URL: {source}")
    owner, repo = m.group(1), m.group(2)
    ref = m.group(4) or "main"
    path = (m.group(5) or "").lstrip("/")
    return owner, repo, ref, path


def _fetch_github_skills(source: str) -> list[tuple[str, str]]:
    """返回 [(filename, content), ...]。

    支持两种仓库结构：
    1. 扁平：目录下直接放 *.md
    2. 子目录：每个 skill 一个子目录，内含 SKILL.md（如 karpathy-skills 格式）
    """
    owner, repo, ref, path = _github_url_to_parts(source)

    # 单文件（blob URL）
    if "/blob/" in source:
        raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{ref}/{path}"
        filename = Path(path).name
        return [(filename, _fetch_raw(raw_url))]

    # 目录或仓库根
    api_path = f"repos/{owner}/{repo}/contents/{path}"
    if ref != "main":
        api_path += f"?ref={ref}"

    try:
        items = _gh_api(api_path)
    except Exception as e:
        raise RuntimeError(f"GitHub API 请求失败: {e}\n提示：安装 gh CLI 并登录可绕过限速") from e

    if not isinstance(items, list):
        raise RuntimeError(f"API 返回格式异常（期望列表，实际: {type(items).__name__}）")

    results = []
    for item in items:
        # 扁平结构：直接是 .md 文件
        if item.get("type") == "file" and item["name"].endswith(".md") and item["name"] not in ("README.md", "CLAUDE.md", "CURSOR.md", "EXAMPLES.md"):
            try:
                content = _fetch_raw(item["download_url"])
                results.append((item["name"], content))
                click.echo(f"  ✓ {item['name']}")
            except Exception as e:
                click.echo(_warn(f"跳过 {item['name']}: {e}"))

        # 子目录结构：进入子目录找 SKILL.md（karpathy-skills 格式）
        elif item.get("type") == "dir" and not item["name"].startswith("."):
            sub_api_path = f"repos/{owner}/{repo}/contents/{item['path']}"
            if ref != "main":
                sub_api_path += f"?ref={ref}"
            try:
                sub_items = _gh_api(sub_api_path)
                if isinstance(sub_items, list):
                    for sub in sub_items:
                        if sub.get("type") == "file" and sub["name"].upper() == "SKILL.MD":
                            content = _fetch_raw(sub["download_url"])
                            # 文件名用目录名（如 karpathy-guidelines.md）
                            filename = f"{item['name']}.md"
                            results.append((filename, content))
                            click.echo(f"  ✓ {item['name']}/SKILL.md → {filename}")
            except Exception as e:
                click.echo(_warn(f"跳过子目录 {item['name']}: {e}"))

    return results


# ─────────────────────────── CLI ────────────────────────────

@click.group()
def cli():
    """Skills Orchestrator — 编译时 Skill 治理工具"""
    pass


@cli.command()
@click.option("--config", "-c", default="config/skills.yaml", help="配置文件路径")
@click.option("--output", "-o", default="AGENTS.md", help="输出文件路径")
@click.option("--zone", "-z", default=None, help="指定 Zone ID，不传则自动探测")
def build(config: str, output: str, zone: Optional[str]):
    """编译配置，生成 AGENTS.md"""
    try:
        parser = Parser(config)
        cfg = parser.parse()
        click.echo(_ok(f"解析完成: {len(cfg.skills)} skills, {len(cfg.zones)} zones"))

        target_zone = None
        if zone:
            target_zone = next((z for z in cfg.zones if z.id == zone), None)
            if not target_zone:
                raise ValueError(f"Zone '{zone}' 不存在")
        else:
            manifest = Manifest()
            enforcer = Enforcer(cfg, manifest)
            target_zone = enforcer.detect_zone(os.getcwd())

        click.echo(_ok(f"使用 Zone: {target_zone.name} ({target_zone.id})"))

        resolver = Resolver(cfg)
        resolved = resolver.resolve(target_zone)
        click.echo(
            _ok(
                f"冲突解决: "
                + click.style(f"{len(resolved.forced_skills)} forced", fg="green")
                + ", "
                + click.style(f"{len(resolved.passive_skills)} passive", fg="yellow")
                + ", "
                + click.style(f"{len(resolved.blocked_skills)} blocked", fg="red")
            )
        )

        compressor = Compressor(resolved)
        manifest = compressor.compress()
        agents_md = compressor.generate_agents_md(manifest, resolved.active_zone)

        output_path = Path(output)
        output_path.write_text(agents_md, encoding="utf-8")
        click.echo(_ok(f"输出: {output_path}"))

    except Exception as e:
        click.echo(_err(str(e)), err=True)
        raise SystemExit(1)


@cli.command()
@click.option("--config", "-c", default="config/skills.yaml", help="配置文件路径")
def validate(config: str):
    """验证配置合法性（不生成文件）"""
    try:
        parser = Parser(config)
        cfg = parser.parse()

        resolver = Resolver(cfg)
        resolved = resolver.resolve()

        click.echo(_ok("配置验证通过"))
        click.echo(f"  Zones:  {len(cfg.zones)}")
        click.echo(f"  Skills: {len(cfg.skills)}")
        click.echo(f"  Combos: {len(cfg.combos)}")

        if resolved.forced_skills:
            click.echo(f"\n{click.style('Forced', fg='green', bold=True)} ({len(resolved.forced_skills)})")
            for s in resolved.forced_skills:
                click.echo(f"  {click.style('✓', fg='green')} {s.id}: {s.name}")

        if resolved.passive_skills:
            click.echo(f"\n{click.style('Passive', fg='yellow', bold=True)} ({len(resolved.passive_skills)})")
            for s in resolved.passive_skills:
                click.echo(f"  {click.style('○', fg='yellow')} {s.id}: {s.name}")

        if resolved.blocked_skills:
            click.echo(f"\n{click.style('Blocked', fg='red', bold=True)} ({len(resolved.blocked_skills)})")
            for s in resolved.blocked_skills:
                reason = resolved.block_reasons.get(s.id, "冲突声明")
                click.echo(f"  {click.style('✗', fg='red')} {s.id}: {s.name}")
                click.echo(f"    {click.style('→', fg='red')} {reason}")

    except Exception as e:
        click.echo(_err(str(e)), err=True)
        raise SystemExit(1)


@cli.command()
@click.option("--workdir", "-w", default=".", help="工作目录")
@click.option("--config", "-c", default="config/skills.yaml", help="配置文件路径")
def inspect(workdir: str, config: str):
    """检查指定目录命中哪个 Zone"""
    try:
        parser = Parser(config)
        cfg = parser.parse()

        manifest = Manifest()
        enforcer = Enforcer(cfg, manifest)
        zone = enforcer.detect_zone(workdir)

        click.echo(f"工作目录: {Path(workdir).resolve()}")
        click.echo(_ok(f"命中 Zone: {click.style(zone.name, bold=True)} ({zone.id})"))
        click.echo(f"  load_policy: {zone.load_policy}")
        click.echo(f"  priority:    {zone.priority}")

    except Exception as e:
        click.echo(_err(str(e)), err=True)
        raise SystemExit(1)


@cli.command()
@click.option("--config", "-c", default="config/skills.yaml", help="配置文件路径")
def status(config: str):
    """显示所有 skills 及状态（forced / passive / blocked）"""
    try:
        parser = Parser(config)
        cfg = parser.parse()

        resolver = Resolver(cfg)
        resolved = resolver.resolve()

        click.echo(f"\n{click.style('Forced Skills', fg='green', bold=True)} — 强制加载")
        if resolved.forced_skills:
            for s in resolved.forced_skills:
                click.echo(f"  {click.style('✓', fg='green')} {click.style(s.id, bold=True)}: {s.name}")
                click.echo(f"    priority={s.priority}  tags=[{', '.join(s.tags)}]")
        else:
            click.echo("  （无）")

        click.echo(f"\n{click.style('Passive Skills', fg='yellow', bold=True)} — 按需加载")
        if resolved.passive_skills:
            for s in resolved.passive_skills:
                click.echo(f"  {click.style('○', fg='yellow')} {click.style(s.id, bold=True)}: {s.name}")
                click.echo(f"    priority={s.priority}  tags=[{', '.join(s.tags)}]")
        else:
            click.echo("  （无）")

        click.echo(f"\n{click.style('Blocked Skills', fg='red', bold=True)} — 已拦截")
        if resolved.blocked_skills:
            for s in resolved.blocked_skills:
                reason = resolved.block_reasons.get(s.id, "冲突声明")
                click.echo(f"  {click.style('✗', fg='red')} {click.style(s.id, bold=True)}: {s.name}")
                click.echo(f"    {click.style('→', fg='red')} {reason}")
        else:
            click.echo("  （无）")

        click.echo("")

    except Exception as e:
        click.echo(_err(str(e)), err=True)
        raise SystemExit(1)


@cli.command()
@click.option("--skills-dir", "-d", default="./skills", help="Skills 目录")
@click.option("--output", "-o", default="skills.yaml", help="输出配置文件路径")
def init(skills_dir: str, output: str):
    """交互式初始化，从本地 skills 目录生成 skills.yaml"""
    skills_path = Path(skills_dir)

    if not skills_path.exists():
        if click.confirm(f"目录 {skills_dir} 不存在，是否创建？", default=True):
            skills_path.mkdir(parents=True)
            click.echo(_ok(f"已创建目录: {skills_path}"))
        else:
            click.echo("已取消")
            return

    md_files = sorted(skills_path.glob("*.md"))
    if not md_files:
        click.echo(_warn(f"{skills_dir} 中没有 .md 文件，请先添加 skill 文件"))
        return

    click.echo(f"\n找到 {len(md_files)} 个 skill 文件，开始配置：\n")

    entries = []
    for md_file in md_files:
        content = md_file.read_text(encoding="utf-8")
        meta = _parse_frontmatter(content)

        click.echo(click.style(f"─── {md_file.name} ───", bold=True))
        skill_id = meta.get("id", md_file.stem)
        default_name = meta.get("name", md_file.stem.replace("-", " ").title())
        default_summary = meta.get("summary", "")
        default_tags = ", ".join(meta.get("tags", []))

        name = click.prompt("  名称", default=default_name)
        summary = click.prompt("  简介", default=default_summary)
        tags_str = click.prompt("  标签（逗号分隔）", default=default_tags)
        policy = click.prompt("  加载策略", default="free",
                              type=click.Choice(["require", "free"]), show_choices=True)
        priority = click.prompt("  优先级 (0-999)", default=50, type=int)

        entries.append({
            "id": meta.get("id", md_file.stem),
            "name": name,
            "path": f"${{SKILLS_ROOT}}/{md_file.name}",
            "summary": summary,
            "tags": [t.strip() for t in tags_str.split(",") if t.strip()],
            "load_policy": policy,
            "priority": priority,
            "zones": ["default"],
            "conflict_with": [],
        })
        click.echo("")

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

    click.echo(_ok(f"生成 {output_path}，包含 {len(entries)} 个 skills"))
    click.echo(f"\n下一步：")
    click.echo(f"  export SKILLS_ROOT={skills_path.resolve()}")
    click.echo(f"  skills-orchestrator build --config {output_path}")


@cli.command()
@click.argument("target_name", type=click.Choice(list(TARGET_REGISTRY.keys())))
@click.option("--config", "-c", default="config/skills.yaml", help="配置文件路径")
@click.option("--zone", "-z", default=None, help="指定 Zone ID，不传则自动探测")
@click.option("--full", is_flag=True, help="全量导出：所有 skill 完整内容（不分 forced/passive）")
@click.option("--summary", is_flag=True, help="摘要模式：passive skill 只导出摘要（仅对 hermes/openclaw 有效，它们默认全量）")
@click.option("--output", "-o", default=None, help="输出路径（仅 agents-md target 使用，默认 AGENTS.md）")
@click.option("--base-dir", default=None, help="目标根目录（hermes/openclaw 使用，默认自动检测）")
@click.option("--dry-run", is_flag=True, help="预览导出结果，不实际写入文件")
def sync(target_name: str, config: str, zone: Optional[str], full: bool, summary: bool, output: Optional[str], base_dir: Optional[str], dry_run: bool):
    """将 skills 同步到外部 Agent 的 skill 目录

    \b
    hermes / openclaw：默认全量导出（--full 隐含），加 --summary 降级为摘要
    agents-md / copilot：默认 forced 完整 + passive 摘要，加 --full 全量导出

    \b
    示例：
      skills-orchestrator sync hermes
      skills-orchestrator sync hermes --summary
      skills-orchestrator sync openclaw
      skills-orchestrator sync agents-md
      skills-orchestrator sync agents-md --full
      skills-orchestrator sync hermes --dry-run
    """
    try:
        parser = Parser(config)
        cfg = parser.parse()

        # 确定 Zone
        target_zone = None
        if zone:
            target_zone = next((z for z in cfg.zones if z.id == zone), None)
            if not target_zone:
                raise ValueError(f"Zone '{zone}' 不存在")
        else:
            manifest = Manifest()
            enforcer = Enforcer(cfg, manifest)
            target_zone = enforcer.detect_zone(os.getcwd())

        click.echo(_ok(f"使用 Zone: {target_zone.name} ({target_zone.id})"))

        # 解析冲突
        resolver = Resolver(cfg)
        resolved = resolver.resolve(target_zone)

        # 根据 target 类型自动决定 full 语义
        # hermes/openclaw：默认全量（外部 agent 自己管理加载），--summary 可降级
        # agents-md/copilot：默认 forced 完整 + passive 摘要，--full 可升级
        _FULL_BY_DEFAULT = {"hermes", "openclaw"}
        if target_name in _FULL_BY_DEFAULT:
            if summary:
                full = False  # 用户显式要求摘要
            else:
                full = True   # 默认全量
        # agents-md / copilot: full 由用户 --full flag 决定，默认 False

        forced_count = len(resolved.forced_skills)
        passive_count = len(resolved.passive_skills)
        blocked_count = len(resolved.blocked_skills)

        if full:
            click.echo(
                f"  "
                + click.style("--full 模式", fg="cyan", bold=True)
                + f": 导出 {forced_count + passive_count} 个 skill 完整内容"
            )
        else:
            click.echo(
                f"  "
                + click.style(f"{forced_count} forced", fg="green")
                + " 完整内容 + "
                + click.style(f"{passive_count} passive", fg="yellow")
                + " 摘要"
                + (f" + {click.style(str(blocked_count) + ' blocked', fg='red')}（跳过）" if blocked_count else "")
            )

        if dry_run:
            click.echo(f"\n{click.style('[dry-run]', fg='yellow')} 目标: {target_name}")
            engine = SyncEngine(resolved, full=full)
            # 列出将要导出的 skills
            if full:
                all_skills = list(resolved.forced_skills) + list(resolved.passive_skills)
                for skill in all_skills:
                    click.echo(f"  {click.style('✓', fg='green')} {skill.id}: {skill.name} (完整)")
            else:
                for skill in resolved.forced_skills:
                    click.echo(f"  {click.style('✓', fg='green')} {skill.id}: {skill.name} (完整)")
                for skill in resolved.passive_skills:
                    click.echo(f"  {click.style('○', fg='yellow')} {skill.id}: {skill.name} (摘要)")
            click.echo(f"\n{click.style('[dry-run]', fg='yellow')} 未写入任何文件")
            return

        # 构建 Registry（让 SyncEngine 支持继承合并）
        from .mcp.registry import SkillRegistry
        registry = SkillRegistry(config)

        # 创建 target
        kwargs = {}
        if target_name == "agents-md" and output:
            kwargs["output_path"] = output
        if target_name in ("hermes", "openclaw") and base_dir:
            kwargs["base_dir"] = base_dir

        target = get_target(target_name, **kwargs)
        click.echo(f"\n同步到: {target.name}")

        # 执行同步
        engine = SyncEngine(resolved, full=full, registry=registry)
        count = engine.sync_to(target)

        click.echo(_ok(f"已同步 {count} 个 skill 到 {target.name}"))

    except Exception as e:
        click.echo(_err(str(e)), err=True)
        raise SystemExit(1)


@cli.command("import")
@click.argument("source")
@click.option("--skills-dir", "-d", default="./skills", help="本地 skills 存放目录")
@click.option("--config", "-c", default="config/skills.yaml", help="配置文件路径（追加导入记录）")
@click.option("--dry-run", is_flag=True, help="预览导入结果，不实际写入文件")
def import_skill(source: str, skills_dir: str, config: str, dry_run: bool):
    """从 GitHub 导入 skill 文件并注册到 skills.yaml

    \b
    示例：
      skills-orchestrator import https://github.com/user/repo
      skills-orchestrator import https://github.com/user/repo/tree/main/skills
      skills-orchestrator import https://github.com/user/repo/blob/main/my-skill.md
    """
    skills_path = Path(skills_dir)
    if not dry_run:
        skills_path.mkdir(parents=True, exist_ok=True)

    click.echo(f"来源: {source}\n")

    try:
        if "github.com" in source:
            files = _fetch_github_skills(source)
        elif source.startswith("http") and source.endswith(".md"):
            filename = source.rsplit("/", 1)[-1]
            content = _fetch_raw(source)
            files = [(filename, content)]
        else:
            raise ValueError("支持的来源：GitHub URL（repo / 目录 / 单文件）或以 .md 结尾的原始 URL")
    except Exception as e:
        click.echo(_err(str(e)), err=True)
        raise SystemExit(1)

    if not files:
        click.echo(_warn("未找到任何 .md 文件"))
        return

    click.echo(f"\n共 {len(files)} 个文件：")

    new_entries = []
    for filename, content in files:
        meta = _parse_frontmatter(content)
        stem = Path(filename).stem
        skill_id = meta.get("id", _slugify(stem))
        entry = {
            "id": skill_id,
            "name": meta.get("name", stem.replace("-", " ").title()),
            "path": f"${{SKILLS_ROOT}}/{filename}",
            "summary": meta.get("summary", f"从 {source} 导入"),
            "tags": meta.get("tags", []),
            "load_policy": meta.get("load_policy", "free"),
            "priority": int(meta.get("priority", 50)),
            "zones": ["default"],
            "conflict_with": [],
        }

        if dry_run:
            click.echo(f"  {click.style('[dry-run]', fg='yellow')} {filename}")
            click.echo(f"    id={skill_id}  name={entry['name']}")
            click.echo(f"    summary={entry['summary'][:60]}...")
        else:
            target = skills_path / filename
            target.write_text(content, encoding="utf-8")
            click.echo(f"  {click.style('✓', fg='green')} {target}")
            new_entries.append(entry)

    if dry_run:
        click.echo(f"\n{click.style('[dry-run]', fg='yellow')} 未写入任何文件")
        return

    if new_entries:
        click.echo("")
        _append_skills_to_yaml(config, new_entries)
        click.echo(f"\n下一步：")
        click.echo(f"  export SKILLS_ROOT={skills_path.resolve()}")
        click.echo(f"  skills-orchestrator build")


@cli.command()
@click.option("--config", "-c", default="config/skills.yaml", help="配置文件路径")
def serve(config: str):
    """启动 MCP Skills Server（stdio 模式，供 Claude Code 连接）

    \b
    在 .claude/settings.json 里添加：
    {
      "mcpServers": {
        "skills-orchestrator": {
          "command": "skills-orchestrator",
          "args": ["serve", "--config", "/path/to/skills.yaml"]
        }
      }
    }
    """
    import asyncio
    from .mcp.server import run_stdio

    config_path = str(Path(config).resolve())
    click.echo(_ok(f"Skills MCP Server 启动中..."), err=True)
    click.echo(f"  配置: {config_path}", err=True)

    try:
        from .mcp.registry import SkillRegistry
        reg = SkillRegistry(config_path)
        click.echo(_ok(f"已加载 {len(reg.all())} 个 skill"), err=True)
    except Exception as e:
        click.echo(_err(f"加载失败: {e}"), err=True)
        raise SystemExit(1)

    asyncio.run(run_stdio(config_path))


@cli.command("mcp-test")
@click.argument("tool_name")
@click.argument("args_json", default="{}")
@click.option("--config", "-c", default="config/skills.yaml", help="配置文件路径")
def mcp_test(tool_name: str, args_json: str, config: str):
    """在命令行测试 MCP 工具调用（不启动 server）

    \b
    示例：
      skills-orchestrator mcp-test list_skills '{}'
      skills-orchestrator mcp-test search_skills '{"query": "git branch workflow"}'
      skills-orchestrator mcp-test get_skill '{"id": "karpathy-guidelines"}'
      skills-orchestrator mcp-test suggest_combo '{"requirement": "部署 Node.js 微服务"}'
      skills-orchestrator mcp-test pipeline_start '{"pipeline_id": "full-dev"}'
    """
    from .mcp.registry import SkillRegistry
    from .mcp.tools import ToolExecutor

    config_path = str(Path(config).resolve())
    try:
        registry = SkillRegistry(config_path)
        executor = ToolExecutor(registry)
        arguments = json.loads(args_json)
        results = executor.execute(tool_name, arguments)
        for r in results:
            click.echo(r.text)
    except json.JSONDecodeError as e:
        click.echo(_err(f"JSON 解析失败: {e}"), err=True)
        raise SystemExit(1)
    except Exception as e:
        click.echo(_err(str(e)), err=True)
        raise SystemExit(1)


# ──────────────────────── Pipeline 子命令 ────────────────────────

@cli.group()
def pipeline():
    """Pipeline 流程编排管理"""
    pass


@pipeline.command("list")
def pipeline_list():
    """列出可用的 Pipeline"""
    pipelines_dir = os.path.join(os.path.dirname(__file__), "..", "config", "pipelines")
    pipelines_dir = os.path.normpath(pipelines_dir)

    if not os.path.isdir(pipelines_dir):
        click.echo(_warn("没有找到 pipeline 配置目录"))
        return

    yaml_files = sorted(f for f in os.listdir(pipelines_dir) if f.endswith(".yaml"))
    if not yaml_files:
        click.echo(_warn("没有可用的 Pipeline"))
        return

    click.echo(f"\n可用的 Pipeline（{len(yaml_files)} 个）：\n")
    for f in yaml_files:
        pipeline_id = f.replace(".yaml", "")
        filepath = os.path.join(pipelines_dir, f)
        try:
            with open(filepath, encoding="utf-8") as fh:
                data = yaml.safe_load(fh)
            name = data.get("name", pipeline_id)
            desc = data.get("description", "")
            steps = data.get("steps", [])
            step_count = len(steps)
            click.echo(f"  {click.style(pipeline_id, bold=True)} — {name}")
            click.echo(f"    {desc}")
            click.echo(f"    {step_count} 个步骤")
            click.echo("")
        except Exception:
            click.echo(f"  {click.style(pipeline_id, bold=True)} — (解析失败)")
            click.echo("")


@pipeline.command("start")
@click.argument("pipeline_id")
@click.option("--context", "-x", default="{}", help="初始上下文 JSON，如 '{\"scope_is_trivial\": true}'")
@click.option("--config", "-c", default="config/skills.yaml", help="配置文件路径")
def pipeline_start(pipeline_id: str, context: str, config: str):
    """启动一个 Pipeline 运行

    \b
    示例：
      skills-orchestrator pipeline start full-dev
      skills-orchestrator pipeline start quick-fix
      skills-orchestrator pipeline start full-dev --context '{"scope_is_trivial": true}'
    """
    from .mcp.registry import SkillRegistry
    from .mcp.tools import ToolExecutor

    config_path = str(Path(config).resolve())
    try:
        registry = SkillRegistry(config_path)
        executor = ToolExecutor(registry)
        ctx = json.loads(context)
        results = executor.execute("pipeline_start", {"pipeline_id": pipeline_id, "context": ctx})
        for r in results:
            click.echo(r.text)
    except json.JSONDecodeError as e:
        click.echo(_err(f"JSON 解析失败: {e}"), err=True)
        raise SystemExit(1)
    except Exception as e:
        click.echo(_err(str(e)), err=True)
        raise SystemExit(1)


@pipeline.command("status")
@click.option("--run-id", "-r", default=None, help="运行 ID")
@click.option("--pipeline-id", "-p", default=None, help="Pipeline ID")
def pipeline_status(run_id: Optional[str], pipeline_id: Optional[str]):
    """查看 Pipeline 运行状态"""
    from .mcp.tools import ToolExecutor

    # pipeline_status 不需要 registry，但 ToolExecutor 需要
    try:
        executor = ToolExecutor.__new__(ToolExecutor)
        executor._registry = None
        executor._searcher = None
        executor._pipelines_dir = None
        executor._pipelines = {}
        executor._store = None
        args = {}
        if run_id:
            args["run_id"] = run_id
        if pipeline_id:
            args["pipeline_id"] = pipeline_id
        results = executor.execute("pipeline_status", args)
        for r in results:
            click.echo(r.text)
    except Exception as e:
        click.echo(_err(str(e)), err=True)
        raise SystemExit(1)


@pipeline.command("advance")
@click.argument("run_id")
@click.argument("pipeline_id")
@click.option("--artifacts", "-a", default="[]", help="产出列表 JSON，如 '[\"implementation_plan\"]'")
@click.option("--context", "-x", default="{}", help="上下文更新 JSON")
@click.option("--config", "-c", default="config/skills.yaml", help="配置文件路径")
def pipeline_advance(run_id: str, pipeline_id: str, artifacts: str, context: str, config: str):
    """推进 Pipeline 到下一步

    \b
    示例：
      skills-orchestrator pipeline advance <run_id> full-dev
      skills-orchestrator pipeline advance <run_id> full-dev --artifacts '["implementation_plan"]'
    """
    from .mcp.registry import SkillRegistry
    from .mcp.tools import ToolExecutor

    config_path = str(Path(config).resolve())
    try:
        registry = SkillRegistry(config_path)
        executor = ToolExecutor(registry)
        arts = json.loads(artifacts)
        ctx = json.loads(context)
        results = executor.execute("pipeline_advance", {
            "run_id": run_id,
            "pipeline_id": pipeline_id,
            "artifacts": arts,
            "context_updates": ctx,
        })
        for r in results:
            click.echo(r.text)
    except json.JSONDecodeError as e:
        click.echo(_err(f"JSON 解析失败: {e}"), err=True)
        raise SystemExit(1)
    except Exception as e:
        click.echo(_err(str(e)), err=True)
        raise SystemExit(1)


@pipeline.command("resume")
@click.option("--run-id", "-r", default=None, help="运行 ID（不传则恢复最近一次）")
@click.option("--pipeline-id", "-p", default=None, help="Pipeline ID")
def pipeline_resume(run_id: Optional[str], pipeline_id: Optional[str]):
    """恢复中断的 Pipeline 运行"""
    from .mcp.tools import ToolExecutor

    try:
        executor = ToolExecutor.__new__(ToolExecutor)
        executor._registry = None
        executor._searcher = None
        executor._pipelines_dir = None
        executor._pipelines = {}
        executor._store = None
        args = {}
        if run_id:
            args["run_id"] = run_id
        if pipeline_id:
            args["pipeline_id"] = pipeline_id
        results = executor.execute("pipeline_resume", args)
        for r in results:
            click.echo(r.text)
    except Exception as e:
        click.echo(_err(str(e)), err=True)
        raise SystemExit(1)


if __name__ == "__main__":
    cli()
