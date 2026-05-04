#!/usr/bin/env python3
"""Skills Orchestrator CLI"""

import hashlib
import json
import os
import re
import urllib.request
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import click
import yaml

from . import __version__
from .compiler import Parser, Resolver, Compressor, SkillsLock
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


def _parse_context(context_str: str) -> dict:
    """解析 context 参数：支持 JSON 字符串或 @文件路径。"""
    if context_str.strip().startswith("@"):
        filepath = Path(context_str.strip()[1:]).resolve()
        # 安全检查：文件必须在当前工作目录内，防止路径穿越
        cwd = Path.cwd().resolve()
        try:
            filepath.relative_to(cwd)
        except ValueError:
            raise click.BadParameter(f"安全限制：context 文件必须在当前目录内: {filepath}")
        if not filepath.exists():
            raise click.BadParameter(f"context 文件不存在: {filepath}")
        return json.loads(filepath.read_text(encoding="utf-8"))
    return json.loads(context_str)


def _resolve_pipelines_dir(config_path: Optional[str] = None) -> Path:
    """统一解析 pipelines 目录，优先级：
    1. 各 pipeline 命令的 --pipelines-dir 参数（已实现）
    2. config 文件同级目录的 pipelines/
    3. 当前目录 config/pipelines
    4. 包内 config/pipelines（开发环境 fallback）
    """
    # 2. config 文件同级目录
    if config_path:
        config_dir = Path(config_path).parent
        pipelines_dir = config_dir / "pipelines"
        if pipelines_dir.is_dir():
            return pipelines_dir

    # 3. 当前目录 config/pipelines
    pipelines_dir = Path("config/pipelines")
    if pipelines_dir.is_dir():
        return pipelines_dir

    # 4. 包内 config/pipelines（开发环境 fallback）
    package_pipelines = Path(__file__).parent.parent / "config" / "pipelines"
    if package_pipelines.is_dir():
        return package_pipelines

    return pipelines_dir  # 返回默认路径（即使不存在）


def _load_pipeline(pipeline_id: str, config_path: Optional[str] = None):
    """加载 Pipeline 定义，返回 Pipeline 对象或 None"""
    from skills_orchestrator.pipeline.loader import PipelineLoader

    pipelines_dir = _resolve_pipelines_dir(config_path)
    yaml_path = pipelines_dir / f"{pipeline_id}.yaml"
    if not yaml_path.exists():
        return None
    loader = PipelineLoader()
    try:
        return loader.load(str(yaml_path))
    except yaml.YAMLError as e:
        click.echo(f"Pipeline YAML 解析失败: {e}", err=True)
        return None
    except Exception as e:
        click.echo(f"加载 Pipeline 失败: {e}", err=True)
        return None


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
    """将文本转换为 slug 格式，保留中文、字母、数字、连字符"""
    # 保留字母、数字、中文、连字符
    result = re.sub(r"[^\w\u4e00-\u9fff-]", "-", text.lower()).strip("-")
    # 兜底：如果结果为空，返回基于 SHA-1 的稳定 ID（跨进程确定性）
    if not result or result.strip("-") == "":
        return f"skill-{hashlib.sha1(text.encode()).hexdigest()[:8]}"
    return result


def _append_skills_to_yaml(config_path: str, new_entries: list[dict]) -> None:
    """把新 skill 条目追加到现有 skills.yaml，如不存在则创建最小配置。"""
    path = Path(config_path)
    if path.exists():
        with open(path, encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}
    else:
        raw = {
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

    click.echo(
        _ok(f"追加 {added} 个 skill 到 {config_path}（跳过 {len(new_entries) - added} 个已存在）")
    )


# ─────────────────────────── GitHub import helpers ────────────────────────────


def _gh_api(api_path: str) -> object:
    """优先用 gh CLI（已认证，无限速），失败则回退到 urllib。"""
    import subprocess

    try:
        result = subprocess.run(["gh", "api", api_path], capture_output=True, text=True, timeout=15)
        if result.returncode == 0:
            return json.loads(result.stdout)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # 回退：未认证的 GitHub API
    url = f"https://api.github.com/{api_path.lstrip('/')}"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "skills-orchestrator/1.0",
            "Accept": "application/vnd.github.v3+json",
        },
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())


def _validate_github_url(url: str) -> bool:
    """验证 URL 是否为合法的 GitHub 域名，防止 SSRF 攻击"""
    try:
        parsed = urlparse(url)
        # 只允许 github.com 和 raw.githubusercontent.com
        return parsed.hostname in (
            "github.com",
            "raw.githubusercontent.com",
            "api.github.com",
        )
    except Exception:
        return False


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
        if (
            item.get("type") == "file"
            and item["name"].endswith(".md")
            and not item["name"].lower().startswith("readme")
            and item["name"] not in ("CLAUDE.md", "CURSOR.md", "EXAMPLES.md")
        ):
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
@click.version_option(version=__version__, prog_name="skills-orchestrator")
def cli():
    """Skills Orchestrator — 编译时 Skill 治理工具"""
    pass


@cli.command()
@click.option("--config", "-c", default="config/skills.yaml", help="配置文件路径")
@click.option("--output", "-o", default="AGENTS.md", help="输出文件路径")
@click.option("--zone", "-z", default=None, help="指定 Zone ID，不传则自动探测")
@click.option("--lock", is_flag=True, help="同时生成 skills.lock.json 保证可复现性")
def build(config: str, output: str, zone: Optional[str], lock: bool):
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
                "冲突解决: "
                + click.style(f"{len(resolved.forced_skills)} forced", fg="green")
                + ", "
                + click.style(f"{len(resolved.passive_skills)} passive", fg="yellow")
                + ", "
                + click.style(f"{len(resolved.blocked_skills)} blocked", fg="red")
            )
        )

        compressor = Compressor(resolved, all_skills=cfg.skills)
        manifest = compressor.compress()
        agents_md = compressor.generate_agents_md(manifest, resolved.active_zone)

        output_path = Path(output)
        output_path.write_text(agents_md, encoding="utf-8")
        click.echo(_ok(f"输出: {output_path}"))

        # 生成 skills.lock.json
        if lock:
            lock_path = output_path.parent / "skills.lock.json"
            locker = SkillsLock(resolved)
            locker.write(str(lock_path))
            click.echo(_ok(f"Lock: {lock_path}"))

    except Exception as e:
        click.echo(_err(str(e)), err=True)
        raise SystemExit(1)


@cli.command()
@click.option("--config", "-c", default="config/skills.yaml", help="配置文件路径")
@click.option("--zone", "-z", default=None, help="指定 Zone ID，不传则使用 default zone")
@click.option("--check-lock", default=None, help="检查 skills.lock.json 是否过期")
def validate(config: str, zone: Optional[str], check_lock: Optional[str]):
    """验证配置合法性（不生成文件）"""
    try:
        parser = Parser(config)
        cfg = parser.parse()

        target_zone = None
        if zone:
            target_zone = next((z for z in cfg.zones if z.id == zone), None)
            if not target_zone:
                raise ValueError(f"Zone '{zone}' 不存在")

        resolver = Resolver(cfg)
        resolved = resolver.resolve(target_zone)

        click.echo(_ok("配置验证通过"))
        if target_zone:
            click.echo(f"  Zone:   {target_zone.name} ({target_zone.id})")
        click.echo(f"  Zones:  {len(cfg.zones)}")
        click.echo(f"  Skills: {len(cfg.skills)}")
        click.echo(f"  Combos: {len(cfg.combos)}")

        if resolved.forced_skills:
            click.echo(
                f"\n{click.style('Forced', fg='green', bold=True)} ({len(resolved.forced_skills)})"
            )
            for s in resolved.forced_skills:
                click.echo(f"  {click.style('✓', fg='green')} {s.id}: {s.name}")

        if resolved.passive_skills:
            click.echo(
                f"\n{click.style('Passive', fg='yellow', bold=True)} ({len(resolved.passive_skills)})"
            )
            for s in resolved.passive_skills:
                click.echo(f"  {click.style('○', fg='yellow')} {s.id}: {s.name}")

        if resolved.blocked_skills:
            click.echo(
                f"\n{click.style('Blocked', fg='red', bold=True)} ({len(resolved.blocked_skills)})"
            )
            for s in resolved.blocked_skills:
                reason = resolved.block_reasons.get(s.id, "冲突声明")
                click.echo(f"  {click.style('✗', fg='red')} {s.id}: {s.name}")
                click.echo(f"    {click.style('→', fg='red')} {reason}")

        # 检查 skills.lock 是否过期
        if check_lock:
            lock_path = Path(check_lock)
            if not lock_path.exists():
                raise click.ClickException(f"Lock 文件不存在: {lock_path}")
            else:
                issues = SkillsLock.check(resolved, str(lock_path))
                if issues:
                    click.echo(
                        f"\n{click.style('Lock 差异', fg='yellow', bold=True)} ({len(issues)})"
                    )
                    for issue in issues:
                        click.echo(f"  {issue}")
                    # 有差异时退出码为 1（用于 CI）
                    raise SystemExit(1)
                else:
                    click.echo(_ok("Lock 校验通过: 所有 skill 与 lock 一致"))

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
@click.option("--zone", "-z", default=None, help="指定 Zone ID，不传则使用 default zone")
def status(config: str, zone: Optional[str]):
    """显示所有 skills 及状态（forced / passive / blocked）"""
    try:
        parser = Parser(config)
        cfg = parser.parse()

        target_zone = None
        if zone:
            target_zone = next((z for z in cfg.zones if z.id == zone), None)
            if not target_zone:
                raise ValueError(f"Zone '{zone}' 不存在")

        resolver = Resolver(cfg)
        resolved = resolver.resolve(target_zone)
        if target_zone:
            click.echo(f"Zone: {target_zone.name} ({target_zone.id})\n")

        click.echo(f"\n{click.style('Forced Skills', fg='green', bold=True)} — 强制加载")
        if resolved.forced_skills:
            for s in resolved.forced_skills:
                click.echo(
                    f"  {click.style('✓', fg='green')} {click.style(s.id, bold=True)}: {s.name}"
                )
                click.echo(f"    priority={s.priority}  tags=[{', '.join(s.tags)}]")
        else:
            click.echo("  （无）")

        click.echo(f"\n{click.style('Passive Skills', fg='yellow', bold=True)} — 按需加载")
        if resolved.passive_skills:
            for s in resolved.passive_skills:
                click.echo(
                    f"  {click.style('○', fg='yellow')} {click.style(s.id, bold=True)}: {s.name}"
                )
                click.echo(f"    priority={s.priority}  tags=[{', '.join(s.tags)}]")
        else:
            click.echo("  （无）")

        click.echo(f"\n{click.style('Blocked Skills', fg='red', bold=True)} — 已拦截")
        if resolved.blocked_skills:
            for s in resolved.blocked_skills:
                reason = resolved.block_reasons.get(s.id, "冲突声明")
                click.echo(
                    f"  {click.style('✗', fg='red')} {click.style(s.id, bold=True)}: {s.name}"
                )
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
    # 也扫描子目录结构（如 skills/quality/refactoring.md → skills/quality/ 下 .md 文件）
    for sub_skill in sorted(skills_path.rglob("*.md")):
        if sub_skill not in md_files:
            md_files.append(sub_skill)
    # 排除非 skill 文件
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
            # 非交互模式：直接使用 frontmatter 值（缺字段用默认值）
            name = default_name
            summary = default_summary
            tags_list = (
                [t.strip() for t in default_tags.split(",") if t.strip()]
                if isinstance(default_tags, str)
                else default_tags
            )
            policy = default_policy
            priority = default_priority
            click.echo(f"  {md_file.name} → {skill_id} ({policy}, p{priority})")
        else:
            # 交互模式：逐一询问
            click.echo(click.style(f"─── {md_file.name} ───", bold=True))
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


@cli.command()
@click.argument("target_name", type=click.Choice(list(TARGET_REGISTRY.keys())))
@click.option("--config", "-c", default="config/skills.yaml", help="配置文件路径")
@click.option("--zone", "-z", default=None, help="指定 Zone ID，不传则自动探测")
@click.option(
    "--full",
    is_flag=True,
    help="全量导出：当前 Zone 内所有可见 skill 的完整内容（不分 forced/passive）",
)
@click.option(
    "--summary",
    is_flag=True,
    help="摘要模式：passive skill 只导出摘要（仅对 hermes/openclaw 有效，它们默认全量）",
)
@click.option(
    "--output",
    "-o",
    default=None,
    help="输出路径（agents-md / copilot target 使用，默认各 target 自带路径）",
)
@click.option("--base-dir", default=None, help="目标根目录（hermes/openclaw 使用，默认自动检测）")
@click.option("--dry-run", is_flag=True, help="预览导出结果，不实际写入文件")
def sync(
    target_name: str,
    config: str,
    zone: Optional[str],
    full: bool,
    summary: bool,
    output: Optional[str],
    base_dir: Optional[str],
    dry_run: bool,
):
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
                full = True  # 默认全量
        # agents-md / copilot: full 由用户 --full flag 决定，默认 False

        forced_count = len(resolved.forced_skills)
        passive_count = len(resolved.passive_skills)
        blocked_count = len(resolved.blocked_skills)

        if full:
            click.echo(
                "  "
                + click.style("--full 模式", fg="cyan", bold=True)
                + f": 导出 {forced_count + passive_count} 个 skill 完整内容"
            )
        else:
            click.echo(
                "  "
                + click.style(f"{forced_count} forced", fg="green")
                + " 完整内容 + "
                + click.style(f"{passive_count} passive", fg="yellow")
                + " 摘要"
                + (
                    f" + {click.style(str(blocked_count) + ' blocked', fg='red')}（跳过）"
                    if blocked_count
                    else ""
                )
            )

        if dry_run:
            click.echo(f"\n{click.style('[dry-run]', fg='yellow')} 目标: {target_name}")
            # 列出将要导出的 skills
            if full:
                all_skills_list = list(resolved.forced_skills) + list(resolved.passive_skills)
                for skill in all_skills_list:
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

        registry = SkillRegistry(config, zone_id=target_zone.id if target_zone else None)

        # 创建 target
        kwargs = {}
        if target_name in ("agents-md", "copilot") and output:
            kwargs["output_path"] = output
        if target_name in ("hermes", "openclaw") and base_dir:
            kwargs["base_dir"] = base_dir

        target = get_target(target_name, **kwargs)
        click.echo(f"\n同步到: {target.name}")

        # 执行同步
        engine = SyncEngine(resolved, full=full, registry=registry, all_skills=cfg.skills)
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
@click.option("--force", is_flag=True, help="强制覆盖已存在的文件")
def import_skill(source: str, skills_dir: str, config: str, dry_run: bool, force: bool):
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
        if not _validate_github_url(source):
            raise ValueError(
                "安全限制：只支持 GitHub URL (github.com, raw.githubusercontent.com)\n"
                "支持的来源：GitHub repo / 目录 / 单文件，或 raw.githubusercontent.com 直链"
            )

        parsed_host = urlparse(source).hostname or ""
        if parsed_host == "raw.githubusercontent.com":
            # raw 直链：单文件，直接下载
            if not source.endswith(".md"):
                raise ValueError("raw.githubusercontent.com 链接必须以 .md 结尾")
            filename = source.rsplit("/", 1)[-1]
            content = _fetch_raw(source)
            files = [(filename, content)]
        else:
            files = _fetch_github_skills(source)
    except Exception as e:
        click.echo(_err(str(e)), err=True)
        raise SystemExit(1)

    if not files:
        click.echo(_warn("未找到任何 .md 文件"))
        if "github.com" in source and "/tree/" not in source and "/blob/" not in source:
            click.echo("  提示：尝试指定子目录，例如：")
            click.echo(f"    skills-orchestrator import {source.rstrip('/')}/tree/main/skills")
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
            # 检查文件是否已存在，防止静默覆盖
            if target.exists() and not force:
                click.echo(
                    f"  {click.style('⚠', fg='yellow')} {target} 已存在，跳过（使用 --force 强制覆盖）"
                )
                continue
            target.write_text(content, encoding="utf-8")
            click.echo(f"  {click.style('✓', fg='green')} {target}")
            new_entries.append(entry)

    if dry_run:
        click.echo(f"\n{click.style('[dry-run]', fg='yellow')} 未写入任何文件")
        return

    if new_entries:
        click.echo("")
        _append_skills_to_yaml(config, new_entries)
        click.echo("\n下一步：")
        click.echo(f"  export SKILLS_ROOT={skills_path.resolve()}")
        click.echo("  skills-orchestrator build")


@cli.command()
@click.option("--config", "-c", default="config/skills.yaml", help="配置文件路径")
@click.option("--zone", "-z", default=None, help="指定 MCP 使用的 zone id")
def serve(config: str, zone: str | None):
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

    # 检查 mcp 包是否已安装
    try:
        from .mcp.server import run_stdio
    except ImportError as e:
        missing = str(e).replace("No module named ", "").strip("'")
        click.echo(_err(f"缺少依赖: {missing}"), err=True)
        click.echo(_err("请运行: pip install skills-orchestrator"), err=True)
        click.echo(_err("或本地开发: pip install -e ."), err=True)
        raise SystemExit(1)

    config_path = str(Path(config).resolve())
    click.echo(_ok("Skills MCP Server 启动中..."), err=True)
    click.echo(f"  配置: {config_path}", err=True)
    if zone:
        click.echo(f"  Zone: {zone}", err=True)

    try:
        from .mcp.registry import SkillRegistry

        reg = SkillRegistry(config_path, zone_id=zone)
        click.echo(_ok(f"已加载 {len(reg.all())} 个 skill"), err=True)
    except Exception as e:
        click.echo(_err(f"加载失败: {e}"), err=True)
        raise SystemExit(1)

    pipelines_dir = _resolve_pipelines_dir(config)
    asyncio.run(run_stdio(config_path, zone_id=zone, pipelines_dir=str(pipelines_dir)))


@cli.command("mcp-test")
@click.argument("tool_name")
@click.argument("args_json", default="{}")
@click.option("--config", "-c", default="config/skills.yaml", help="配置文件路径")
@click.option("--zone", "-z", default=None, help="指定 zone id")
def mcp_test(tool_name: str, args_json: str, config: str, zone: Optional[str]):
    """在命令行测试 MCP 工具调用（不启动 server）

    \b
    示例：
      skills-orchestrator mcp-test list_skills '{}'
      skills-orchestrator mcp-test search_skills '{"query": "git branch workflow"}'
      skills-orchestrator mcp-test get_skill '{"id": "karpathy-guidelines"}'
      skills-orchestrator mcp-test suggest_combo '{"requirement": "部署 Node.js 微服务"}'
      skills-orchestrator mcp-test pipeline_start '{"pipeline_id": "full-dev"}'
      skills-orchestrator mcp-test list_skills '{}' -z enterprise
    """
    from .mcp.registry import SkillRegistry
    from .mcp.tools import ToolExecutor

    config_path = str(Path(config).resolve())
    try:
        registry = SkillRegistry(config_path, zone_id=zone)
        pipelines_dir = _resolve_pipelines_dir(config)
        executor = ToolExecutor(registry, pipelines_dir=str(pipelines_dir))
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
@click.option("--detail", "-d", is_flag=True, help="显示详细版列表（带分类和预览）")
@click.option("--compact", "-c", is_flag=True, help="显示紧凑版列表（适合窄终端）")
@click.option(
    "--config", "-f", default="config/skills.yaml", help="配置文件路径（用于定位 pipelines 目录）"
)
def pipeline_list(detail: bool, compact: bool, config: str):
    """列出可用的 Pipeline

    默认显示简洁版，使用 --detail 查看详细版，--compact 查看紧凑版
    """
    pipelines_dir = _resolve_pipelines_dir(config)

    if not pipelines_dir.is_dir():
        click.echo(_warn(f"没有找到 pipeline 配置目录: {pipelines_dir}"))
        return

    yaml_files = sorted(f for f in pipelines_dir.iterdir() if f.suffix == ".yaml")
    if not yaml_files:
        click.echo(_warn("没有可用的 Pipeline"))
        return

    # 紧凑版显示
    if compact:
        click.echo(f"\n可用 Pipeline ({len(yaml_files)}个):\n")
        for f in yaml_files:
            pipeline_id = f.stem
            try:
                data = yaml.safe_load(f.read_text(encoding="utf-8"))
                name = data.get("name", pipeline_id)
                steps = data.get("steps", [])
                step_count = len(steps)

                # 简单的分类图标
                if step_count <= 2:
                    icon = "⚡"
                elif step_count <= 4:
                    icon = "🛠️"
                else:
                    icon = "📋"

                click.echo(
                    f"  {icon} {click.style(pipeline_id, bold=True):20} {name:30} ({step_count}步)"
                )
            except Exception:
                click.echo(f"  ❌ {click.style(pipeline_id, bold=True):20} (解析失败)")
        return

    # 详细版显示
    if detail:
        click.echo("\n" + "=" * 60)
        click.echo("📋 可用的 Pipeline 模板".center(60))
        click.echo("=" * 60)

        for f in yaml_files:
            pipeline_id = f.stem

            try:
                data = yaml.safe_load(f.read_text(encoding="utf-8"))

                name = data.get("name", pipeline_id)
                desc = data.get("description", "")
                steps = data.get("steps", [])
                step_count = len(steps)

                # 分类信息
                if step_count <= 2:
                    length_category, length_icon = "短流程", "🟢"
                elif step_count <= 4:
                    length_category, length_icon = "中流程", "🟡"
                else:
                    length_category, length_icon = "长流程", "🔴"

                # 使用场景分类
                scenario_map = {
                    "bug-fix": "bug修复",
                    "full-dev": "完整开发",
                    "quick-fix": "快速修复",
                    "review-only": "代码审查",
                    "security-audit": "安全审查",
                }
                scenario_category = scenario_map.get(pipeline_id, "其他")

                # 步骤摘要
                step_names = []
                for step in steps:
                    step_id = step.get("id", "unknown")
                    step_skill = step.get("skill", "unknown")
                    step_names.append(f"{step_id}({step_skill})")

                # 输出格式
                click.echo(f"\n🔷 {name}")
                click.echo(f"   ID: {pipeline_id}")
                click.echo(f"   📝 {desc}")
                click.echo(f"   📊 {length_icon} {length_category} | {step_count} 个步骤")
                click.echo(f"   🎯 使用场景: {scenario_category}")
                click.echo(f"   🚀 启动命令: skills-orchestrator pipeline start {pipeline_id}")

                # 步骤预览（最多显示3个）
                if step_names:
                    preview = " → ".join(step_names[:3])
                    if len(step_names) > 3:
                        preview += f" → ... (共{step_count}步)"
                    click.echo(f"   🛣️  流程预览: {preview}")

                click.echo("   " + "─" * 50)

            except Exception as e:
                click.echo(f"\n❌ 加载 {pipeline_id} 时出错: {e}")

        click.echo("\n" + "=" * 60)
        click.echo("💡 使用提示:")
        click.echo("  • 使用 'skills-orchestrator pipeline start <ID>' 启动")
        click.echo("  • 添加 '--context @文件.json' 传递上下文")
        click.echo('  • 使用 \'--context "{\\"key\\": \\"value\\"}"\' 传递简单上下文')
        click.echo("=" * 60)
        return

    # 默认简洁版
    click.echo(f"\n可用的 Pipeline（{len(yaml_files)} 个）：\n")
    for f in yaml_files:
        pipeline_id = f.stem
        try:
            data = yaml.safe_load(f.read_text(encoding="utf-8"))
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
@click.option(
    "--context",
    "-x",
    default="{}",
    help="初始上下文 JSON 或 @文件路径，如 '{\"skip_review\": true}' 或 @ctx.json",
)
@click.option("--config", "-c", default="config/skills.yaml", help="配置文件路径")
@click.option("--zone", "-z", default=None, help="指定 zone id")
@click.option("--pipelines-dir", default=None, help="Pipeline 定义目录（默认为 config/pipelines）")
def pipeline_start(
    pipeline_id: str, context: str, config: str, zone: Optional[str], pipelines_dir: Optional[str]
):
    """启动一个 Pipeline 运行

    \b
    示例：
      skills-orchestrator pipeline start full-dev
      skills-orchestrator pipeline start quick-fix
      skills-orchestrator pipeline start bug-fix --context '{"skip_review": true}'
      skills-orchestrator pipeline start bug-fix --context @context.json
      skills-orchestrator pipeline start quick-fix -z enterprise
      skills-orchestrator pipeline start quick-fix --pipelines-dir /path/to/pipelines
    """
    from .mcp.registry import SkillRegistry
    from .mcp.tools import ToolExecutor

    config_path = str(Path(config).resolve())
    resolved_pipelines_dir = (
        Path(pipelines_dir) if pipelines_dir else _resolve_pipelines_dir(config)
    )

    # 使用 _load_pipeline 统一加载，避免重复
    pipeline = _load_pipeline(pipeline_id, config)
    if pipeline is None:
        click.echo(_err(f"Pipeline '{pipeline_id}' 不存在或加载失败"), err=True)
        raise SystemExit(1)

    try:
        registry = SkillRegistry(config_path, zone_id=zone)
        executor = ToolExecutor(registry, pipelines_dir=str(resolved_pipelines_dir))
        ctx = _parse_context(context)
        results = executor.execute(
            "pipeline_start",
            {"pipeline_id": pipeline_id, "context": ctx},
        )
        for r in results:
            click.echo(r.text)
    except json.JSONDecodeError as e:
        click.echo(_err(f"JSON 解析失败: {e}"), err=True)
        raise SystemExit(1)
    except Exception as e:
        click.echo(_err(str(e)), err=True)
        raise SystemExit(1)


@pipeline.command("status")
@click.argument("pipeline_id", required=False, default=None)
@click.option("--run-id", "-r", default=None, help="运行 ID")
@click.option("--config", "-c", default="config/skills.yaml", help="配置文件路径")
@click.option("--pipelines-dir", default=None, help="Pipeline 定义目录（默认为 config/pipelines）")
def pipeline_status(
    pipeline_id: Optional[str], run_id: Optional[str], config: str, pipelines_dir: Optional[str]
):
    """查看 Pipeline 运行状态

    \b
    示例：
      skills-orchestrator pipeline status quick-fix
      skills-orchestrator pipeline status quick-fix --run-id abc123
      skills-orchestrator pipeline status  # 查看最近的运行
    """
    from skills_orchestrator.pipeline.store import RunStateStore

    try:
        store = RunStateStore()

        # 加载 RunState
        if run_id and pipeline_id:
            state = store.load(pipeline_id, run_id)
        else:
            state = store.load_latest(pipeline_id or None)

        if state is None:
            click.echo(_warn("没有找到运行记录。"))
            return

        # 加载 Pipeline 定义（用于显示步骤详情）
        pipeline = _load_pipeline(state.pipeline_id, config)
        lines = [
            f"Pipeline: {state.pipeline_id}  Run: {state.run_id}",
            f"状态: {state.status}  当前步骤: {state.current_step or '(已完成)'}",
            f"开始时间: {state.started_at}  更新时间: {state.updated_at}",
            "",
            "步骤历史：",
        ]
        for h in state.step_history:
            status_icon = {"completed": "✓", "skipped": "⏭", "failed": "✗"}.get(h["status"], "?")
            reason = f" ({h.get('reason', '')})" if h.get("reason") else ""
            lines.append(f"  {status_icon} {h['step']} — {h['status']}{reason}")

        if state.current_step and pipeline:
            step = pipeline.get_step(state.current_step)
            if step and step.gate:
                lines.append("")
                lines.append(f"门禁要求: 产出 '{step.gate.must_produce}'")
                if step.gate.min_length:
                    lines.append(f"  最小长度: {step.gate.min_length} 字符")

        if state.context:
            lines.append("")
            lines.append(f"上下文键: {', '.join(state.context.keys())}")

        click.echo("\n".join(lines))
    except Exception as e:
        click.echo(_err(str(e)), err=True)
        raise SystemExit(1)


@pipeline.command("advance")
@click.argument("pipeline_id")
@click.option("--run-id", "-r", default=None, help="运行 ID（不传则自动使用最近一次进行中的运行）")
@click.option(
    "--artifacts", "-a", default="[]", help="产出列表 JSON，如 '[\"implementation_plan\"]'"
)
@click.option(
    "--context",
    "-x",
    default="{}",
    help="上下文更新 JSON 或 @文件路径，如 '{\"done\": true}' 或 @ctx.json",
)
@click.option("--config", "-c", default="config/skills.yaml", help="配置文件路径")
@click.option("--zone", "-z", default=None, help="指定 zone id")
@click.option("--pipelines-dir", default=None, help="Pipeline 定义目录（默认为 config/pipelines）")
def pipeline_advance(
    pipeline_id: str,
    run_id: Optional[str],
    artifacts: str,
    context: str,
    config: str,
    zone: Optional[str],
    pipelines_dir: Optional[str],
):
    """推进 Pipeline 到下一步

    \b
    示例：
      skills-orchestrator pipeline advance bug-fix
      skills-orchestrator pipeline advance bug-fix --run-id abc123
      skills-orchestrator pipeline advance bug-fix --artifacts '["root_cause"]'
      skills-orchestrator pipeline advance bug-fix --context @updates.json
      skills-orchestrator pipeline advance bug-fix -z enterprise
    """
    from .mcp.registry import SkillRegistry
    from .mcp.tools import ToolExecutor
    from .pipeline.store import RunStateStore

    config_path = str(Path(config).resolve())
    try:
        # 自动找最新运行（run_id 未指定时）
        if not run_id:
            store = RunStateStore()
            state = store.load_latest(pipeline_id)
            if state is None:
                click.echo(
                    _err(f"没有找到 '{pipeline_id}' 的运行记录，请先执行 pipeline start"), err=True
                )
                raise SystemExit(1)
            if state.status == "completed":
                click.echo(
                    _warn(f"Pipeline '{pipeline_id}' 最近一次运行已完成（run: {state.run_id}）")
                )
                click.echo("  如需重新运行，请执行 pipeline start")
                return
            run_id = state.run_id
            click.echo(f"  自动使用运行 ID: {click.style(run_id, bold=True)}")

        registry = SkillRegistry(config_path, zone_id=zone)
        resolved_pipelines_dir = (
            Path(pipelines_dir) if pipelines_dir else _resolve_pipelines_dir(config)
        )
        executor = ToolExecutor(registry, pipelines_dir=str(resolved_pipelines_dir))
        arts = json.loads(artifacts)
        ctx = _parse_context(context)
        results = executor.execute(
            "pipeline_advance",
            {
                "run_id": run_id,
                "pipeline_id": pipeline_id,
                "artifacts": arts,
                "context_updates": ctx,
            },
        )
        for r in results:
            click.echo(r.text)
    except json.JSONDecodeError as e:
        click.echo(_err(f"JSON 解析失败: {e}"), err=True)
        raise SystemExit(1)
    except Exception as e:
        click.echo(_err(str(e)), err=True)
        raise SystemExit(1)


@pipeline.command("resume")
@click.argument("pipeline_id", required=False, default=None)
@click.option("--run-id", "-r", default=None, help="运行 ID（不传则恢复最近一次）")
@click.option("--config", "-c", default="config/skills.yaml", help="配置文件路径")
@click.option("--pipelines-dir", default=None, help="Pipeline 定义目录（默认为 config/pipelines）")
def pipeline_resume(
    pipeline_id: Optional[str], run_id: Optional[str], config: str, pipelines_dir: Optional[str]
):
    """恢复中断的 Pipeline 运行

    \b
    示例：
      skills-orchestrator pipeline resume quick-fix
      skills-orchestrator pipeline resume quick-fix --run-id abc123
      skills-orchestrator pipeline resume  # 恢复最近的运行
    """
    from skills_orchestrator.pipeline.engine import PipelineEngine
    from skills_orchestrator.pipeline.store import RunStateStore

    try:
        store = RunStateStore()

        # 加载 RunState
        if run_id and pipeline_id:
            state = store.load(pipeline_id, run_id)
        else:
            state = store.load_latest(pipeline_id or None)

        if state is None:
            click.echo(_warn("没有找到可恢复的运行记录。"))
            return

        if state.status == "completed":
            click.echo(f"Pipeline 已完成，无需恢复。Run: {state.run_id}")
            return

        pipeline = _load_pipeline(state.pipeline_id, config)
        if pipeline is None:
            click.echo(_err(f"Pipeline 不存在: {state.pipeline_id}"), err=True)
            raise SystemExit(1)

        engine = PipelineEngine(pipeline)
        state = engine.resume(state)
        store.save(state)

        step = pipeline.get_step(state.current_step) if state.current_step else None
        lines = [
            f"Pipeline '{pipeline.name}' 已恢复！",
            f"Run ID: {state.run_id}",
            f"当前步骤: {state.current_step} (skill: {step.skill if step else '?'})",
            f"状态: {state.status}",
        ]
        if step and step.gate:
            lines.append("")
            lines.append(f"⚠ 门禁要求: 完成此步骤前必须产出 '{step.gate.must_produce}'")
            if step.gate.min_length:
                lines.append(f"  最小长度: {step.gate.min_length} 字符")

        lines.append("")
        lines.append(
            "使用 skills-orchestrator pipeline advance <pipeline_id> --run-id <run_id> 推进下一步。"
        )
        click.echo("\n".join(lines))
    except Exception as e:
        click.echo(_err(str(e)), err=True)
        raise SystemExit(1)


if __name__ == "__main__":
    cli()
