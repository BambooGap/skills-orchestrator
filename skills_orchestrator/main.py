#!/usr/bin/env python3
"""Skills Orchestrator CLI"""

import json
import os
from pathlib import Path
from typing import Optional

import click
import yaml

from . import __version__
from .security import (
    console_safe_symbol,
    console_safe_text,
    safe_child_path,
    validate_identifier,
)
from .compiler import Parser, Resolver, Compressor, SkillsLock
from .enforcer import Enforcer
from .sync.targets import get_target, SyncEngine, TARGET_REGISTRY
from .models import Manifest
from .cli.init_cmd import init as _init_cmd
from .cli.import_cmd import import_skill as _import_cmd


# ─────────────────────────── helpers ────────────────────────────


def _sym(symbol: str, fallback: str) -> str:
    return console_safe_symbol(symbol, fallback)


def _ok(msg: str) -> str:
    return click.style(console_safe_symbol("✓", "OK"), fg="green") + f" {console_safe_text(msg)}"


def _warn(msg: str) -> str:
    return click.style(console_safe_symbol("⚠", "!"), fg="yellow") + f" {console_safe_text(msg)}"


def _err(msg: str) -> str:
    return click.style(console_safe_symbol("✗", "X"), fg="red") + f" {console_safe_text(msg)}"


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
    pipeline_id = validate_identifier(pipeline_id, "pipeline_id")
    yaml_path = safe_child_path(pipelines_dir, f"{pipeline_id}.yaml")
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


# ─────────────────────────── CLI ────────────────────────────


@click.group()
@click.version_option(version=__version__, prog_name="skills-orchestrator")
def cli():
    """Skills Orchestrator — 编译时 Skill 治理工具"""
    pass


# Register migrated init command from cli/init_cmd.py
cli.add_command(_init_cmd, "init")

# Register migrated import command from cli/import_cmd.py
cli.add_command(_import_cmd)


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
                click.echo(f"  {click.style(_sym('✓', 'OK'), fg='green')} {s.id}: {s.name}")

        if resolved.passive_skills:
            click.echo(
                f"\n{click.style('Passive', fg='yellow', bold=True)} ({len(resolved.passive_skills)})"
            )
            for s in resolved.passive_skills:
                click.echo(f"  {click.style(_sym('○', 'o'), fg='yellow')} {s.id}: {s.name}")

        if resolved.blocked_skills:
            click.echo(
                f"\n{click.style('Blocked', fg='red', bold=True)} ({len(resolved.blocked_skills)})"
            )
            for s in resolved.blocked_skills:
                reason = resolved.block_reasons.get(s.id, "冲突声明")
                click.echo(f"  {click.style(_sym('✗', 'X'), fg='red')} {s.id}: {s.name}")
                click.echo(f"    {click.style(_sym('→', '->'), fg='red')} {reason}")

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

        click.echo(
            console_safe_text(f"\n{click.style('Forced Skills', fg='green', bold=True)} — 强制加载")
        )
        if resolved.forced_skills:
            for s in resolved.forced_skills:
                click.echo(
                    f"  {click.style(_sym('✓', 'OK'), fg='green')} {click.style(s.id, bold=True)}: {s.name}"
                )
                click.echo(f"    priority={s.priority}  tags=[{', '.join(s.tags)}]")
        else:
            click.echo("  （无）")

        click.echo(
            console_safe_text(
                f"\n{click.style('Passive Skills', fg='yellow', bold=True)} — 按需加载"
            )
        )
        if resolved.passive_skills:
            for s in resolved.passive_skills:
                click.echo(
                    f"  {click.style(_sym('○', 'o'), fg='yellow')} {click.style(s.id, bold=True)}: {s.name}"
                )
                click.echo(f"    priority={s.priority}  tags=[{', '.join(s.tags)}]")
        else:
            click.echo("  （无）")

        click.echo(
            console_safe_text(f"\n{click.style('Blocked Skills', fg='red', bold=True)} — 已拦截")
        )
        if resolved.blocked_skills:
            for s in resolved.blocked_skills:
                reason = resolved.block_reasons.get(s.id, "冲突声明")
                click.echo(
                    f"  {click.style(_sym('✗', 'X'), fg='red')} {click.style(s.id, bold=True)}: {s.name}"
                )
                click.echo(f"    {click.style(_sym('→', '->'), fg='red')} {reason}")
        else:
            click.echo("  （无）")

        click.echo("")

    except Exception as e:
        click.echo(_err(str(e)), err=True)
        raise SystemExit(1)


# init command migrated to cli/init_cmd.py — registered below


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
                    click.echo(
                        f"  {click.style(_sym('✓', 'OK'), fg='green')} {skill.id}: {skill.name} (完整)"
                    )
            else:
                for skill in resolved.forced_skills:
                    click.echo(
                        f"  {click.style(_sym('✓', 'OK'), fg='green')} {skill.id}: {skill.name} (完整)"
                    )
                for skill in resolved.passive_skills:
                    click.echo(
                        f"  {click.style(_sym('○', 'o'), fg='yellow')} {skill.id}: {skill.name} (摘要)"
                    )
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
            click.echo(console_safe_text(r.text))
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
                    icon = console_safe_text("⚡")
                elif step_count <= 4:
                    icon = console_safe_text("🛠️")
                else:
                    icon = console_safe_text("📋")

                click.echo(
                    f"  {icon} {click.style(pipeline_id, bold=True):20} {name:30} ({step_count}步)"
                )
            except Exception:
                click.echo(
                    console_safe_text(f"  ❌ {click.style(pipeline_id, bold=True):20} (解析失败)")
                )
        return

    # 详细版显示
    if detail:
        click.echo("\n" + "=" * 60)
        click.echo(console_safe_text("📋 可用的 Pipeline 模板".center(60)))
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
                    length_category, length_icon = "短流程", console_safe_text("🟢")
                elif step_count <= 4:
                    length_category, length_icon = "中流程", console_safe_text("🟡")
                else:
                    length_category, length_icon = "长流程", console_safe_text("🔴")

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
                click.echo(console_safe_text(f"\n🔷 {name}"))
                click.echo(f"   ID: {pipeline_id}")
                click.echo(console_safe_text(f"   📝 {desc}"))
                click.echo(
                    console_safe_text(
                        f"   📊 {length_icon} {length_category} | {step_count} 个步骤"
                    )
                )
                click.echo(console_safe_text(f"   🎯 使用场景: {scenario_category}"))
                click.echo(
                    console_safe_text(
                        f"   🚀 启动命令: skills-orchestrator pipeline start {pipeline_id}"
                    )
                )

                # 步骤预览（最多显示3个）
                if step_names:
                    preview = f" {_sym('→', '->')} ".join(step_names[:3])
                    if len(step_names) > 3:
                        preview += f" {_sym('→', '->')} ... (共{step_count}步)"
                    click.echo(console_safe_text(f"   🛣️  流程预览: {preview}"))

                click.echo(console_safe_text("   " + "─" * 50))

            except Exception as e:
                click.echo(console_safe_text(f"\n❌ 加载 {pipeline_id} 时出错: {e}"))

        click.echo("\n" + "=" * 60)
        click.echo(console_safe_text("💡 使用提示:"))
        click.echo(console_safe_text("  • 使用 'skills-orchestrator pipeline start <ID>' 启动"))
        click.echo(console_safe_text("  • 添加 '--context @文件.json' 传递上下文"))
        click.echo(
            console_safe_text('  • 使用 \'--context "{\\"key\\": \\"value\\"}"\' 传递简单上下文')
        )
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
            click.echo(console_safe_text(f"  {click.style(pipeline_id, bold=True)} — {name}"))
            click.echo(f"    {desc}")
            click.echo(f"    {step_count} 个步骤")
            click.echo("")
        except Exception:
            click.echo(console_safe_text(f"  {click.style(pipeline_id, bold=True)} — (解析失败)"))
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
            status_icon = {
                "completed": _sym("✓", "OK"),
                "skipped": _sym("⏭", "SKIP"),
                "failed": _sym("✗", "X"),
            }.get(h["status"], "?")
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

        click.echo(console_safe_text("\n".join(lines)))
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
        click.echo(console_safe_text("\n".join(lines)))
    except Exception as e:
        click.echo(_err(str(e)), err=True)
        raise SystemExit(1)


if __name__ == "__main__":
    cli()
