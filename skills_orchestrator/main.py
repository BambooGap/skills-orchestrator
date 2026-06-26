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
from .cli.check_cmd import check as _check_cmd
from .cli.manifest_cmd import manifest as _manifest_cmd
from .cli.policy_cmd import policy as _policy_cmd
from .cli.schema_cmd import schema as _schema_cmd
from .checker import fatal_error_report, run_check
from .diagnostic import DiagnosticSeverity
from .formatters import format_diagnostics_json, format_diagnostics_sarif


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
    4. 包内 config/pipelines（wheel / sdist）
    5. 仓库根目录 config/pipelines（源码开发 fallback）
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

    # 4. 包内 config/pipelines（wheel / sdist）
    package_pipelines = Path(__file__).parent / "config" / "pipelines"
    if package_pipelines.is_dir():
        return package_pipelines

    # 5. 仓库根目录 config/pipelines（源码开发 fallback）
    source_pipelines = Path(__file__).parent.parent / "config" / "pipelines"
    if source_pipelines.is_dir():
        return source_pipelines

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
    """Skills Orchestrator — SkillOps / instruction-supply-chain control plane."""
    pass


# Register migrated init command from cli/init_cmd.py
cli.add_command(_init_cmd, "init")

# Register migrated import command from cli/import_cmd.py
cli.add_command(_import_cmd)

# Register structured check command from cli/check_cmd.py
cli.add_command(_check_cmd)

# Register instruction inventory and policy export commands
cli.add_command(_manifest_cmd)
cli.add_command(_policy_cmd)
cli.add_command(_schema_cmd)


@cli.command()
@click.option("--config", "-c", default="config/skills.yaml", help="配置文件路径")
@click.option("--output", "-o", default="AGENTS.md", help="输出文件路径")
@click.option("--zone", "-z", default=None, help="指定 Zone ID，不传则自动探测")
@click.option("--lock", is_flag=True, help="同时生成 skills.lock.json 保证可复现性")
def build(config: str, output: str, zone: Optional[str], lock: bool):
    """编译 skill 配置并生成 AGENTS.md。"""
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
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["text", "json", "sarif"]),
    default="text",
    show_default=True,
    help="输出格式；text 保持原有行为",
)
@click.option(
    "--policy-pack",
    "policy_packs",
    multiple=True,
    help="启用内置治理规则包，例如 builtin/team-standard。可重复传入。",
)
def validate(
    config: str,
    zone: Optional[str],
    check_lock: Optional[str],
    output_format: str,
    policy_packs: tuple[str, ...],
):
    """验证配置合法性（不生成文件）"""
    try:
        if output_format != "text":
            report = run_check(
                config, zone_id=zone, check_lock=check_lock, policy_packs=policy_packs
            )
            if output_format == "json":
                click.echo(console_safe_text(format_diagnostics_json(report)), nl=False)
            else:
                click.echo(console_safe_text(format_diagnostics_sarif(report)), nl=False)
            if any(d.severity == DiagnosticSeverity.ERROR for d in report.diagnostics):
                raise SystemExit(1)
            if check_lock and any(d.rule_id == "SO007" for d in report.diagnostics):
                raise SystemExit(1)
            return

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
        if policy_packs:
            report = run_check(
                config,
                zone_id=zone,
                check_lock=check_lock,
                policy_packs=policy_packs,
            )
            summary = report.summary()
            if summary["total"]:
                click.echo(
                    _warn(
                        "Policy findings: "
                        f"{summary['errors']} errors, {summary['warnings']} warnings, "
                        f"{summary['infos']} infos"
                    )
                )
                for diagnostic in report.diagnostics:
                    click.echo(
                        f"  [{diagnostic.severity.value.upper()}] "
                        f"{diagnostic.rule_id}: {diagnostic.message}"
                    )
                if any(d.severity == DiagnosticSeverity.ERROR for d in report.diagnostics):
                    raise SystemExit(1)
            else:
                click.echo(_ok("Policy packs passed"))
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
        if output_format != "text":
            report = fatal_error_report(str(e), config_path=config)
            if output_format == "json":
                click.echo(console_safe_text(format_diagnostics_json(report)), nl=False)
            else:
                click.echo(console_safe_text(format_diagnostics_sarif(report)), nl=False)
            raise SystemExit(1)
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
@click.option(
    "--audit-dir",
    default=None,
    help="可选。写入 MCP JSONL 审计事件的目录；也可用 SKILLS_ORCHESTRATOR_AUDIT_DIR。",
)
@click.option(
    "--max-content-bytes",
    default=None,
    type=int,
    help="运行期注入单个 skill 内容的最大字节数；0 表示不限制。",
)
def serve(
    config: str,
    zone: str | None,
    audit_dir: str | None,
    max_content_bytes: int | None,
):
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
    if audit_dir:
        click.echo(f"  Audit dir: {audit_dir}", err=True)

    try:
        from .mcp.registry import SkillRegistry

        reg = SkillRegistry(config_path, zone_id=zone)
        click.echo(_ok(f"已加载 {len(reg.all())} 个 skill"), err=True)
    except Exception as e:
        click.echo(_err(f"加载失败: {e}"), err=True)
        raise SystemExit(1)

    pipelines_dir = _resolve_pipelines_dir(config)
    asyncio.run(
        run_stdio(
            config_path,
            zone_id=zone,
            pipelines_dir=str(pipelines_dir),
            audit_dir=audit_dir,
            max_content_bytes=max_content_bytes,
        )
    )


@cli.command("mcp-test")
@click.argument("tool_name")
@click.argument("args_json", default="{}")
@click.option("--config", "-c", default="config/skills.yaml", help="配置文件路径")
@click.option("--zone", "-z", default=None, help="指定 zone id")
@click.option(
    "--audit-dir",
    default=None,
    help="可选。写入 MCP JSONL 审计事件的目录；也可用 SKILLS_ORCHESTRATOR_AUDIT_DIR。",
)
@click.option(
    "--max-content-bytes",
    default=None,
    type=int,
    help="运行期注入单个 skill 内容的最大字节数；0 表示不限制。",
)
def mcp_test(
    tool_name: str,
    args_json: str,
    config: str,
    zone: Optional[str],
    audit_dir: str | None,
    max_content_bytes: int | None,
):
    """在命令行测试 MCP 工具调用（不启动 server）

    \b
    示例：
      skills-orchestrator mcp-test list_skills '{}'
      skills-orchestrator mcp-test search_skills '{"query": "git branch workflow"}'
      skills-orchestrator mcp-test get_skill '{"id": "git-worktrees"}'
      skills-orchestrator mcp-test suggest_combo '{"requirement": "部署 Node.js 微服务"}'
      skills-orchestrator mcp-test prepare_context '{"task": "做安全审查"}'
      skills-orchestrator mcp-test pipeline_start '{"pipeline_id": "full-dev"}'
      skills-orchestrator mcp-test list_skills '{}' -z enterprise
    """
    from .mcp.registry import SkillRegistry
    from .mcp.tools import ToolExecutor

    config_path = str(Path(config).resolve())
    try:
        registry = SkillRegistry(config_path, zone_id=zone)
        pipelines_dir = _resolve_pipelines_dir(config)
        executor = ToolExecutor(
            registry,
            pipelines_dir=str(pipelines_dir),
            audit_dir=audit_dir,
            max_content_bytes=max_content_bytes,
        )
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


# ──────────────────────── Integrations 子命令 ────────────────────────


@cli.group()
def integrations():
    """外部 agent 生态集成目录"""
    pass


@integrations.command("list")
@click.option("--layer", default=None, help="按生态层过滤，例如 execution-model")
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["text", "json"]),
    default="text",
    show_default=True,
)
def integrations_list(layer: str | None, output_format: str):
    """列出建议集成的相邻 agent 工具和定位。"""
    from skills_orchestrator.integrations import get_integrations

    rows = get_integrations(layer)
    if output_format == "json":
        payload = {
            "schema_version": "skills-orchestrator.integrations.v1",
            "integrations": [row.to_dict() for row in rows],
        }
        click.echo(json.dumps(payload, ensure_ascii=False, indent=2))
        return

    if not rows:
        click.echo(_warn(f"没有找到 layer={layer} 的集成项"))
        return

    click.echo("Skills Orchestrator integration catalog\n")
    for row in rows:
        click.echo(f"{click.style(row.name, bold=True)} ({row.id})")
        click.echo(f"  layer: {row.layer}")
        click.echo(f"  relationship: {row.relationship}")
        click.echo(f"  strategy: {row.strategy}")
        click.echo(f"  commercial_value: {row.commercial_value}")
        click.echo(f"  url: {row.url}")
        click.echo("")


# ──────────────────────── Registry 子命令 ────────────────────────


@cli.group()
def registry():
    """组织级 skill registry 导出"""
    pass


@registry.command("build")
@click.option(
    "--config-glob",
    "config_globs",
    multiple=True,
    default=("config/skills.yaml",),
    show_default=True,
    help="skills.yaml 路径或 glob；可重复传入。",
)
@click.option("--zone", "-z", default=None, help="指定所有配置使用的 zone id")
@click.option("--output", "-o", default=None, help="写入 registry JSON 文件；默认输出到 stdout")
def registry_build(config_globs: tuple[str, ...], zone: str | None, output: str | None):
    """构建组织级 skill registry JSON。"""
    from skills_orchestrator.org_registry import build_registry, write_registry

    try:
        payload = build_registry(config_globs, zone_id=zone)
        rendered = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
        if output:
            write_registry(payload, output)
            click.echo(_ok(f"Registry written: {output}"))
            click.echo(
                "  "
                + f"configs={payload['summary']['configs']} "
                + f"skills={payload['summary']['skill_refs']} "
                + f"duplicates={payload['summary']['duplicate_skill_ids']}"
            )
            return
        click.echo(console_safe_text(rendered), nl=False)
    except Exception as exc:
        click.echo(_err(str(exc)), err=True)
        raise SystemExit(1)


@registry.command("graph")
@click.option(
    "--config-glob",
    "config_globs",
    multiple=True,
    default=("config/skills.yaml",),
    show_default=True,
    help="skills.yaml 路径或 glob；可重复传入。",
)
@click.option("--zone", "-z", default=None, help="指定所有配置使用的 zone id")
@click.option(
    "--output", "-o", default=None, help="写入 registry graph JSON 文件；默认输出到 stdout"
)
def registry_graph(config_globs: tuple[str, ...], zone: str | None, output: str | None):
    """从 registry 派生结构化治理图 JSON。"""
    from skills_orchestrator.org_registry import (
        build_registry,
        build_registry_graph,
        write_registry_graph,
    )

    try:
        registry_payload = build_registry(config_globs, zone_id=zone)
        graph_payload = build_registry_graph(registry_payload)
        rendered = json.dumps(graph_payload, ensure_ascii=False, indent=2) + "\n"
        if output:
            write_registry_graph(graph_payload, output)
            click.echo(_ok(f"Registry graph written: {output}"))
            click.echo(
                "  "
                + f"nodes={graph_payload['summary']['nodes']} "
                + f"edges={graph_payload['summary']['edges']}"
            )
            return
        click.echo(console_safe_text(rendered), nl=False)
    except Exception as exc:
        click.echo(_err(str(exc)), err=True)
        raise SystemExit(1)


@registry.command("diff")
@click.argument("base")
@click.argument("head")
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["text", "json", "markdown"]),
    default="text",
    show_default=True,
)
@click.option("--output", "-o", default=None, help="写入 diff 文件；默认输出到 stdout")
@click.option("--force", is_flag=True, help="覆盖已存在的 diff 输出文件")
def registry_diff(base: str, head: str, output_format: str, output: str | None, force: bool):
    """比较两个 registry JSON 文件。"""
    from skills_orchestrator.org_registry import diff_registries, format_registry_diff_markdown

    try:
        base_payload = json.loads(Path(base).read_text(encoding="utf-8"))
        head_payload = json.loads(Path(head).read_text(encoding="utf-8"))
        diff = diff_registries(base_payload, head_payload)
        if output_format == "json":
            rendered = json.dumps(diff, ensure_ascii=False, indent=2) + "\n"
        elif output_format == "markdown":
            rendered = format_registry_diff_markdown(diff)
        else:
            summary = diff["summary"]
            lines = [
                "Registry diff: "
                f"{summary['added']} added, {summary['removed']} removed, "
                f"{summary['changed']} changed"
            ]
            for item in diff["changed"]:
                lines.append(
                    f"  changed: {item['registry_key']} ({', '.join(item['changes'].keys())})"
                )
            for item in diff["added"]:
                lines.append(f"  added: {item['registry_key']}")
            for item in diff["removed"]:
                lines.append(f"  removed: {item['registry_key']}")
            for item in diff.get("duplicate_id_changes", []):
                lines.append(f"  duplicate-id: {item['id']} {item['before']} -> {item['after']}")
            rendered = "\n".join(lines) + "\n"

        if output:
            output_path = Path(output)
            if output_path.exists() and not force:
                raise click.ClickException(
                    f"输出文件已存在，未覆盖: {output_path}（如需覆盖请加 --force）"
                )
            output_path.write_text(rendered, encoding="utf-8")
            click.echo(_ok(f"Registry diff written: {output_path}"))
            return
        click.echo(console_safe_text(rendered), nl=False)
    except Exception as exc:
        click.echo(_err(str(exc)), err=True)
        raise SystemExit(1)


@registry.command("comment-body")
@click.argument("markdown_file")
@click.option("--output", "-o", default=None, help="写入 PR comment Markdown；默认输出到 stdout")
@click.option("--force", is_flag=True, help="覆盖已存在的输出文件")
@click.option(
    "--max-chars",
    default=60000,
    show_default=True,
    help="GitHub comment body 最大字符数，超出时截断。",
)
def registry_comment_body(
    markdown_file: str,
    output: str | None,
    force: bool,
    max_chars: int,
):
    """从 registry diff Markdown 生成幂等 PR comment body。"""
    from skills_orchestrator.github_pr import format_registry_diff_comment_file

    try:
        rendered = format_registry_diff_comment_file(markdown_file, max_chars=max_chars)
        if output:
            output_path = Path(output)
            if output_path.exists() and not force:
                raise click.ClickException(
                    f"输出文件已存在，未覆盖: {output_path}（如需覆盖请加 --force）"
                )
            output_path.write_text(rendered, encoding="utf-8")
            click.echo(_ok(f"Registry diff comment body written: {output_path}"))
            return
        click.echo(console_safe_text(rendered), nl=False)
    except Exception as exc:
        click.echo(_err(str(exc)), err=True)
        raise SystemExit(1)


# ──────────────────────── Doctor 子命令 ────────────────────────


@cli.command("doctor")
@click.option("--config", "-c", default="config/skills.yaml", help="配置文件路径")
@click.option("--zone", "-z", default=None, help="指定 zone id")
@click.option(
    "--policy-pack",
    "policy_packs",
    multiple=True,
    default=("builtin/team-standard",),
    show_default=True,
    help="启用内置治理规则包；可重复传入。",
)
@click.option("--check-lock", default=None, help="检查指定 skills.lock.json 是否过期")
@click.option("--agents-md", default="AGENTS.md", help="生成的 AGENTS.md 路径")
@click.option(
    "--profile",
    type=click.Choice(["adopter", "maintainer", "enterprise"]),
    default="adopter",
    show_default=True,
    help="readiness 评分口径：adopter 面向接入仓库，maintainer 面向本项目发版，enterprise 面向证据包试点。",
)
@click.option(
    "--evidence-dir",
    default="evidence",
    show_default=True,
    help="enterprise profile 读取的证据包目录",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["text", "json"]),
    default="text",
    show_default=True,
)
@click.option("--fail-under", default=0, show_default=True, help="分数低于该值时返回非零退出码")
def doctor(
    config: str,
    zone: str | None,
    policy_packs: tuple[str, ...],
    check_lock: str | None,
    agents_md: str,
    profile: str,
    evidence_dir: str,
    output_format: str,
    fail_under: int,
):
    """生成团队 SkillOps readiness 报告。"""
    from skills_orchestrator.doctor import format_doctor_text, run_doctor

    try:
        payload = run_doctor(
            config,
            zone_id=zone,
            policy_packs=policy_packs,
            check_lock=check_lock,
            agents_md=agents_md,
            profile=profile,
            evidence_dir=evidence_dir,
        )
        if output_format == "json":
            click.echo(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            click.echo(console_safe_text(format_doctor_text(payload)), nl=False)
        if fail_under and payload["score"] < fail_under:
            raise SystemExit(1)
    except Exception as exc:
        click.echo(_err(str(exc)), err=True)
        raise SystemExit(1)


# ──────────────────────── Conformance 子命令 ────────────────────────


@cli.group()
def conformance():
    """运行 SkillOps Contract 一致性验证"""
    pass


@conformance.command("run")
@click.option(
    "--config", "-c", default="config/skills.yaml", show_default=True, help="配置文件路径"
)
@click.option("--project-root", default=".", show_default=True, help="adapter inspect 的项目根目录")
@click.option("--zone", "-z", default=None, help="指定 zone id")
@click.option(
    "--policy-pack",
    "policy_packs",
    multiple=True,
    default=("builtin/team-standard",),
    show_default=True,
    help="启用治理规则包；可重复传入。",
)
@click.option(
    "--profile",
    type=click.Choice(["core", "enterprise"]),
    default="core",
    show_default=True,
    help="一致性验证口径。",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["text", "json"]),
    default="text",
    show_default=True,
)
@click.option(
    "--fail-on",
    type=click.Choice(["error", "warning", "never"]),
    default="error",
    show_default=True,
    help="达到指定严重级别时返回非零退出码。",
)
def conformance_run(
    config: str,
    project_root: str,
    zone: str | None,
    policy_packs: tuple[str, ...],
    profile: str,
    output_format: str,
    fail_on: str,
):
    """运行本地 SkillOps Contract 一致性检查。"""
    from skills_orchestrator.conformance import (
        conformance_should_fail,
        format_conformance_text,
        run_conformance,
    )

    try:
        payload = run_conformance(
            config,
            project_root=project_root,
            zone_id=zone,
            policy_packs=policy_packs,
            profile=profile,
            fail_on=fail_on,
        )
        if output_format == "json":
            click.echo(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            click.echo(console_safe_text(format_conformance_text(payload)), nl=False)
        if conformance_should_fail(payload, fail_on):
            raise SystemExit(1)
    except Exception as exc:
        click.echo(_err(str(exc)), err=True)
        raise SystemExit(1)


# ──────────────────────── Explainability 子命令 ────────────────────────


@cli.group()
def explainability():
    """导出 CI-level policy decision explainability"""
    pass


@explainability.command("build")
@click.option("--config", "-c", default="config/skills.yaml", help="配置文件路径")
@click.option("--check-json", default=None, help="复用已有 check --format json 输出")
@click.option("--zone", "-z", default=None, help="指定 zone id")
@click.option("--check-lock", default=None, help="检查指定 skills.lock.json 是否过期")
@click.option(
    "--max-skill-bytes",
    default=20000,
    show_default=True,
    type=int,
    help="SO005 oversized-skill 阈值",
)
@click.option(
    "--policy-pack",
    "policy_packs",
    multiple=True,
    default=(),
    help="启用治理规则包；可重复传入。",
)
@click.option(
    "--fail-on",
    type=click.Choice(["error", "warning", "never"]),
    default="error",
    show_default=True,
    help="解释 CI 是否阻塞时使用的严重级别。",
)
@click.option("--output", "-o", default=None, help="写入 ci-explainability.json；默认 stdout")
@click.option("--force", is_flag=True, help="覆盖已存在的输出文件")
def explainability_build(
    config: str,
    check_json: str | None,
    zone: str | None,
    check_lock: str | None,
    max_skill_bytes: int,
    policy_packs: tuple[str, ...],
    fail_on: str,
    output: str | None,
    force: bool,
):
    """生成机器可读的 CI 失败原因与 policy decision trace。"""
    from skills_orchestrator.explainability import (
        build_ci_explainability,
        build_ci_explainability_from_check_payload,
        format_ci_explainability_json,
    )

    try:
        if check_json:
            check_payload = json.loads(Path(check_json).read_text(encoding="utf-8"))
            payload = build_ci_explainability_from_check_payload(
                check_payload,
                config_path=config,
                fail_on=fail_on,
            )
        else:
            report = run_check(
                config,
                zone_id=zone,
                check_lock=check_lock,
                max_skill_bytes=max_skill_bytes,
                policy_packs=policy_packs,
            )
            payload = build_ci_explainability(report, config_path=config, fail_on=fail_on)
        rendered = format_ci_explainability_json(payload)
        if output:
            output_path = Path(output)
            if output_path.exists() and not force:
                raise click.ClickException(
                    f"输出文件已存在，未覆盖: {output_path}（如需覆盖请加 --force）"
                )
            output_path.write_text(rendered, encoding="utf-8")
            click.echo(_ok(f"CI explainability written: {output_path}"))
            return
        click.echo(console_safe_text(rendered), nl=False)
    except Exception as exc:
        click.echo(_err(str(exc)), err=True)
        raise SystemExit(1)


# ──────────────────────── Evidence 子命令 ────────────────────────


@cli.group()
def evidence():
    """导出 CI/审计/商业交付证据包"""
    pass


@evidence.command("export")
@click.option("--config", "-c", default="config/skills.yaml", help="配置文件路径")
@click.option("--zone", "-z", default=None, help="指定 zone id")
@click.option("--out", "out_dir", default="evidence", show_default=True, help="证据包输出目录")
@click.option(
    "--policy-pack",
    "policy_packs",
    multiple=True,
    default=("builtin/team-standard",),
    show_default=True,
    help="启用内置治理规则包；可重复传入。",
)
@click.option("--check-lock", default=None, help="检查指定 skills.lock.json 是否过期")
@click.option("--agents-md", default="AGENTS.md", help="生成的 AGENTS.md 路径")
@click.option(
    "--previous-bundle-hash",
    default=None,
    help="上一份 evidence bundle hash，用于形成简单 hash chain。",
)
def evidence_export(
    config: str,
    zone: str | None,
    out_dir: str,
    policy_packs: tuple[str, ...],
    check_lock: str | None,
    agents_md: str,
    previous_bundle_hash: str | None,
):
    """导出 check、manifest、policy、doctor、registry 证据文件。"""
    from skills_orchestrator.evidence import export_evidence_bundle

    try:
        bundle = export_evidence_bundle(
            config,
            out_dir,
            zone_id=zone,
            policy_packs=policy_packs,
            check_lock=check_lock,
            agents_md=agents_md,
            previous_bundle_hash=previous_bundle_hash,
        )
        click.echo(_ok(f"Evidence bundle written: {out_dir}"))
        for label, path in bundle["files"].items():
            click.echo(f"  {label}: {path}")
        click.echo(f"  bundle_hash: {bundle['ledger']['bundle_hash']}")
        click.echo(f"  evidence_manifest: {Path(out_dir) / 'evidence-manifest.json'}")
    except Exception as exc:
        click.echo(_err(str(exc)), err=True)
        raise SystemExit(1)


@evidence.command("index")
@click.option(
    "--manifest",
    "manifests",
    multiple=True,
    help="Evidence manifest path or repo-id=path. Can be repeated.",
)
@click.option(
    "--manifest-glob",
    "manifest_globs",
    multiple=True,
    help="Evidence manifest glob; supports ** recursion.",
)
@click.option("--scope-name", default=None, help="Organization or rollout scope name.")
@click.option("--previous-index-hash", default="", help="Previous multi-repo index hash.")
@click.option(
    "--output", "-o", default=None, help="Write multi-repo artifacts JSON; default stdout."
)
@click.option("--force", is_flag=True, help="Overwrite existing output file.")
def evidence_index(
    manifests: tuple[str, ...],
    manifest_globs: tuple[str, ...],
    scope_name: str | None,
    previous_index_hash: str,
    output: str | None,
    force: bool,
):
    """Index multiple evidence manifests as one multi-repo artifact contract."""
    from skills_orchestrator.evidence_index import (
        build_multi_repo_artifacts,
        expand_manifest_inputs,
        format_multi_repo_artifacts_json,
    )

    try:
        manifest_specs = expand_manifest_inputs(manifests, manifest_globs)
        rendered = format_multi_repo_artifacts_json(
            build_multi_repo_artifacts(
                manifest_specs,
                scope_name=scope_name,
                previous_index_hash=previous_index_hash,
            )
        )
        if output:
            output_path = Path(output)
            if output_path.exists() and not force:
                raise click.ClickException(
                    f"输出文件已存在，未覆盖: {output_path}（如需覆盖请加 --force）"
                )
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(rendered, encoding="utf-8")
            click.echo(_ok(f"Multi-repo artifacts index written: {output_path}"))
            return
        click.echo(console_safe_text(rendered), nl=False)
    except Exception as exc:
        click.echo(_err(str(exc)), err=True)
        raise SystemExit(1)


# ──────────────────────── Reviewer 子命令 ────────────────────────


@cli.group()
def reviewer():
    """生成 PR reviewer 可读的 SkillOps 汇总"""
    pass


@reviewer.command("summary")
@click.option("--check-json", default=None, help="check --format json 输出路径")
@click.option("--registry-diff-json", default=None, help="registry diff --format json 输出路径")
@click.option("--registry-diff-markdown", default=None, help="registry diff Markdown 输出路径")
@click.option("--registry-graph", default=None, help="registry graph JSON 输出路径")
@click.option("--evidence-manifest", default=None, help="evidence-manifest.json 输出路径")
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["markdown", "json"]),
    default="markdown",
    show_default=True,
    help="输出格式",
)
@click.option("--output", "-o", default=None, help="写入 reviewer summary 文件；默认 stdout")
@click.option("--force", is_flag=True, help="覆盖已存在的输出文件")
def reviewer_summary(
    check_json: str | None,
    registry_diff_json: str | None,
    registry_diff_markdown: str | None,
    registry_graph: str | None,
    evidence_manifest: str | None,
    output_format: str,
    output: str | None,
    force: bool,
):
    """汇总 check、policy trace、registry graph 和 evidence ledger。"""
    from skills_orchestrator.reviewer import (
        build_reviewer_summary,
        format_reviewer_summary_json,
        render_reviewer_summary_markdown,
    )

    try:
        summary = build_reviewer_summary(
            check_json=check_json,
            registry_diff_json=registry_diff_json,
            registry_diff_markdown=registry_diff_markdown,
            registry_graph=registry_graph,
            evidence_manifest=evidence_manifest,
        )
        rendered = (
            format_reviewer_summary_json(summary)
            if output_format == "json"
            else render_reviewer_summary_markdown(summary)
        )
        if output:
            output_path = Path(output)
            if output_path.exists() and not force:
                raise click.ClickException(
                    f"输出文件已存在，未覆盖: {output_path}（如需覆盖请加 --force）"
                )
            output_path.write_text(rendered, encoding="utf-8")
            click.echo(_ok(f"Reviewer summary written: {output_path}"))
            return
        click.echo(console_safe_text(rendered), nl=False)
    except Exception as exc:
        click.echo(_err(str(exc)), err=True)
        raise SystemExit(1)


# ──────────────────────── Dashboard 子命令 ────────────────────────


@cli.group()
def dashboard():
    """从 SkillOps evidence 生成平台 dashboard 数据"""
    pass


@dashboard.command("snapshot")
@click.option("--evidence-dir", default="evidence", show_default=True, help="evidence bundle 目录")
@click.option("--repository", default=None, help="仓库 full name；默认读取 GITHUB_REPOSITORY")
@click.option("--ref", "ref_name", default=None, help="Git ref；默认读取 GITHUB_REF")
@click.option("--commit", default=None, help="commit SHA；默认读取 GITHUB_SHA")
@click.option("--output", "-o", default=None, help="写入 dashboard snapshot JSON；默认 stdout")
@click.option("--force", is_flag=True, help="覆盖已存在的输出文件")
def dashboard_snapshot(
    evidence_dir: str,
    repository: str | None,
    ref_name: str | None,
    commit: str | None,
    output: str | None,
    force: bool,
):
    """从 evidence-manifest.json 派生 enterprise dashboard snapshot。"""
    from skills_orchestrator.dashboard import (
        build_dashboard_snapshot,
        format_dashboard_snapshot_json,
    )

    try:
        rendered = format_dashboard_snapshot_json(
            build_dashboard_snapshot(
                evidence_dir,
                repository=repository,
                ref=ref_name,
                commit=commit,
            )
        )
        if output:
            output_path = Path(output)
            if output_path.exists() and not force:
                raise click.ClickException(
                    f"输出文件已存在，未覆盖: {output_path}（如需覆盖请加 --force）"
                )
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(rendered, encoding="utf-8")
            click.echo(_ok(f"Dashboard snapshot written: {output_path}"))
            return
        click.echo(console_safe_text(rendered), nl=False)
    except Exception as exc:
        click.echo(_err(str(exc)), err=True)
        raise SystemExit(1)


@dashboard.command("rollup")
@click.option("--snapshot", "snapshots", multiple=True, help="dashboard snapshot JSON 路径")
@click.option(
    "--snapshot-glob",
    "snapshot_globs",
    multiple=True,
    help="dashboard snapshot glob；支持 ** 递归",
)
@click.option("--organization", default=None, help="组织名；默认读取 GITHUB_REPOSITORY_OWNER")
@click.option("--output", "-o", default=None, help="写入 dashboard rollup JSON；默认 stdout")
@click.option("--force", is_flag=True, help="覆盖已存在的输出文件")
def dashboard_rollup(
    snapshots: tuple[str, ...],
    snapshot_globs: tuple[str, ...],
    organization: str | None,
    output: str | None,
    force: bool,
):
    """聚合多个 dashboard snapshot，生成组织级 dashboard rollup。"""
    from skills_orchestrator.dashboard import (
        build_dashboard_rollup,
        expand_snapshot_inputs,
        format_dashboard_rollup_json,
    )

    try:
        snapshot_paths = expand_snapshot_inputs(snapshots, snapshot_globs)
        rendered = format_dashboard_rollup_json(
            build_dashboard_rollup(snapshot_paths, organization=organization)
        )
        if output:
            output_path = Path(output)
            if output_path.exists() and not force:
                raise click.ClickException(
                    f"输出文件已存在，未覆盖: {output_path}（如需覆盖请加 --force）"
                )
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(rendered, encoding="utf-8")
            click.echo(_ok(f"Dashboard rollup written: {output_path}"))
            return
        click.echo(console_safe_text(rendered), nl=False)
    except Exception as exc:
        click.echo(_err(str(exc)), err=True)
        raise SystemExit(1)


# ──────────────────────── Usage 子命令 ────────────────────────


@cli.group()
def usage():
    """MCP 运行期使用审计和团队汇总"""
    pass


@usage.command("report")
@click.option(
    "--audit-dir",
    default=None,
    help="MCP JSONL 审计事件目录；默认读取 SKILLS_ORCHESTRATOR_AUDIT_DIR。",
)
@click.option("--json", "as_json", is_flag=True, help="输出 JSON，便于 CI 或报表系统读取")
def usage_report(audit_dir: str | None, as_json: bool):
    """根据 MCP audit events 生成使用汇总。"""
    from skills_orchestrator.mcp.audit import AUDIT_DIR_ENV, load_events, summarize_events

    events = load_events(audit_dir)
    summary = summarize_events(events)

    if as_json:
        click.echo(json.dumps(summary, ensure_ascii=False, indent=2))
        return

    if not events:
        configured = audit_dir or os.environ.get(AUDIT_DIR_ENV) or "(未设置)"
        click.echo(_warn(f"没有找到 MCP audit events。audit_dir={configured}"))
        click.echo("启用方式: skills-orchestrator serve --audit-dir .skills-audit")
        return

    lines = [
        "Skills Orchestrator usage report",
        f"Events: {summary['events']}",
        "",
        "Tools:",
    ]
    for tool, count in summary["tools"].items():
        lines.append(f"  - {tool}: {count}")

    lines.append("")
    lines.append("Outcomes:")
    for outcome, count in summary["outcomes"].items():
        lines.append(f"  - {outcome}: {count}")

    if summary["top_active_skills"]:
        lines.append("")
        lines.append("Top active skills:")
        for skill_id, count in summary["top_active_skills"].items():
            lines.append(f"  - {skill_id}: {count}")

    lines.append("")
    lines.append(f"Searches with no result: {summary['searches_with_no_result']}")
    click.echo(console_safe_text("\n".join(lines)))


# ──────────────────────── Adapters 子命令 ────────────────────────


@cli.group()
def adapters():
    """生态适配器检测和 scaffold 输出"""
    pass


@adapters.command("inspect")
@click.option("--path", "root", default=".", show_default=True, help="项目根目录")
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["text", "json"]),
    default="text",
    show_default=True,
)
def adapters_inspect(root: str, output_format: str):
    """检测 AGENTS.md、Claude Skills、MCP、OpenAI Agents SDK 等适配面。"""
    from skills_orchestrator.adapters import inspect_adapters

    try:
        payload = inspect_adapters(root)
        if output_format == "json":
            click.echo(json.dumps(payload, ensure_ascii=False, indent=2))
            return
        click.echo("Skills Orchestrator adapter inspection\n")
        for surface in payload["surfaces"]:
            status_text = "detected" if surface["detected"] else "not detected"
            click.echo(f"{click.style(surface['name'], bold=True)} ({surface['id']})")
            click.echo(f"  status: {status_text}")
            click.echo(f"  direction: {surface['direction']}")
            click.echo(f"  authority: {surface['authority']}")
            if surface["paths"]:
                click.echo(f"  paths: {', '.join(surface['paths'])}")
            verification = surface["verification"]
            click.echo(f"  verification: {verification['status']}")
            click.echo(f"  checks: {', '.join(verification['checks'])}")
            click.echo("")
    except Exception as exc:
        click.echo(_err(str(exc)), err=True)
        raise SystemExit(1)


@adapters.group("export")
def adapters_export():
    """输出外部 agent runtime 的最小 scaffold"""
    pass


@adapters_export.command("mcp-client-config")
@click.option("--config", "-c", default="config/skills.yaml", show_default=True)
@click.option("--zone", "-z", default=None, help="可选 zone id")
@click.option("--output", "-o", default=None, help="写入 JSON 文件；默认输出到 stdout")
@click.option("--force", is_flag=True, help="覆盖已存在的输出文件")
def adapters_export_mcp_client_config(
    config: str,
    zone: str | None,
    output: str | None,
    force: bool,
):
    """生成 stdio MCP client config。"""
    from skills_orchestrator.adapters.scaffolds import (
        format_mcp_client_config,
        generate_mcp_client_config,
    )

    try:
        rendered = format_mcp_client_config(generate_mcp_client_config(config, zone=zone))
        _write_optional_output(rendered, output=output, force=force, label="MCP client config")
    except Exception as exc:
        click.echo(_err(str(exc)), err=True)
        raise SystemExit(1)


@adapters_export.command("openai-agents-sdk")
@click.option("--config", "-c", default="config/skills.yaml", show_default=True)
@click.option("--zone", "-z", default=None, help="可选 zone id")
@click.option("--output", "-o", default=None, help="写入 Python scaffold；默认输出到 stdout")
@click.option("--force", is_flag=True, help="覆盖已存在的输出文件")
def adapters_export_openai_agents_sdk(
    config: str,
    zone: str | None,
    output: str | None,
    force: bool,
):
    """生成 OpenAI Agents SDK + MCPServerStdio scaffold。"""
    from skills_orchestrator.adapters.scaffolds import generate_openai_agents_sdk_scaffold

    try:
        rendered = generate_openai_agents_sdk_scaffold(config, zone=zone)
        _write_optional_output(
            rendered, output=output, force=force, label="OpenAI Agents SDK scaffold"
        )
    except Exception as exc:
        click.echo(_err(str(exc)), err=True)
        raise SystemExit(1)


@adapters_export.command("claude-skills")
@click.option("--config", "-c", default="config/skills.yaml", show_default=True)
@click.option(
    "--output-dir",
    "-o",
    default=".claude/skills",
    show_default=True,
    help="写入 Claude Skills bundle 的目录。",
)
@click.option("--manifest-output", default=None, help="可选：写入 export manifest JSON。")
@click.option("--force", is_flag=True, help="覆盖已存在的 SKILL.md")
def adapters_export_claude_skills(
    config: str,
    output_dir: str,
    manifest_output: str | None,
    force: bool,
):
    """导出 Claude Skills */SKILL.md bundles，并保留 SkillOps 治理元数据。"""
    from skills_orchestrator.adapters.scaffolds import (
        export_claude_skill_bundles,
        format_claude_skills_export_manifest,
    )

    try:
        payload = export_claude_skill_bundles(config, output_dir, force=force)
        rendered = format_claude_skills_export_manifest(payload)
        if manifest_output:
            _write_optional_output(
                rendered,
                output=manifest_output,
                force=force,
                label="Claude Skills export manifest",
            )
        click.echo(_ok(f"Claude Skills exported: {payload['summary']['exported']}"))
    except Exception as exc:
        click.echo(_err(str(exc)), err=True)
        raise SystemExit(1)


def _write_optional_output(rendered: str, *, output: str | None, force: bool, label: str) -> None:
    if output:
        output_path = Path(output)
        if output_path.exists() and not force:
            raise click.ClickException(
                f"输出文件已存在，未覆盖: {output_path}（如需覆盖请加 --force）"
            )
        output_path.write_text(rendered, encoding="utf-8")
        click.echo(_ok(f"{label} written: {output_path}"))
        return
    click.echo(console_safe_text(rendered), nl=False)


# ──────────────────────── Supply-chain 子命令 ────────────────────────


@cli.group("supply-chain")
def supply_chain():
    """软件供应链证据输出"""
    pass


@supply_chain.command("sbom")
@click.option("--project-name", default="skills-orchestrator", show_default=True)
@click.option("--output", "-o", default=None, help="写入 CycloneDX JSON 文件；默认输出到 stdout")
@click.option("--force", is_flag=True, help="覆盖已存在的输出文件")
@click.option(
    "--no-dependencies",
    is_flag=True,
    help="只输出当前包组件，不枚举已安装依赖。",
)
def supply_chain_sbom(
    project_name: str,
    output: str | None,
    force: bool,
    no_dependencies: bool,
):
    """生成 Python package CycloneDX SBOM。"""
    from skills_orchestrator.supply_chain import build_python_package_sbom, format_sbom_json

    try:
        sbom = build_python_package_sbom(
            project_name=project_name,
            include_dependencies=not no_dependencies,
        )
        rendered = format_sbom_json(sbom)
        if output:
            output_path = Path(output)
            if output_path.exists() and not force:
                raise click.ClickException(
                    f"输出文件已存在，未覆盖: {output_path}（如需覆盖请加 --force）"
                )
            output_path.write_text(rendered, encoding="utf-8")
            click.echo(_ok(f"Package SBOM written: {output_path}"))
            return
        click.echo(console_safe_text(rendered), nl=False)
    except Exception as exc:
        click.echo(_err(str(exc)), err=True)
        raise SystemExit(1)


@supply_chain.command("container-release")
@click.option("--image", required=True, help="Fully qualified container image name, without tag.")
@click.option("--tag", default="", show_default=True, help="Release tag associated with the image.")
@click.option("--digest", required=True, help="Immutable image digest, for example sha256:<hex>.")
@click.option(
    "--repository", default="", show_default=True, help="Source repository, for example org/repo."
)
@click.option("--commit", default="", show_default=True, help="Source commit SHA.")
@click.option(
    "--workflow-run-url",
    default="",
    show_default=True,
    help="GitHub Actions run URL that produced the image.",
)
@click.option(
    "--sbom-output",
    default="container-sbom.cdx.json",
    show_default=True,
    help="Write container-bound CycloneDX SBOM to this path.",
)
@click.option(
    "--provenance-output",
    default="container-provenance.json",
    show_default=True,
    help="Write SkillOps container provenance to this path.",
)
@click.option("--force", is_flag=True, help="覆盖已存在的输出文件")
@click.option(
    "--no-dependencies",
    is_flag=True,
    help="只输出当前包组件，不枚举已安装依赖。",
)
def supply_chain_container_release(
    image: str,
    tag: str,
    digest: str,
    repository: str,
    commit: str,
    workflow_run_url: str,
    sbom_output: str,
    provenance_output: str,
    force: bool,
    no_dependencies: bool,
):
    """生成绑定到 container digest 的 SBOM 与 release provenance。"""
    from skills_orchestrator.supply_chain import (
        build_container_image_sbom,
        build_container_release_provenance,
        format_provenance_json,
        format_sbom_json,
    )

    try:
        sbom_path = Path(sbom_output)
        provenance_path = Path(provenance_output)
        for output_path in (sbom_path, provenance_path):
            if output_path.exists() and not force:
                raise click.ClickException(
                    f"输出文件已存在，未覆盖: {output_path}（如需覆盖请加 --force）"
                )

        sbom = build_container_image_sbom(
            image=image,
            tag=tag,
            digest=digest,
            include_dependencies=not no_dependencies,
        )
        sbom_path.write_text(format_sbom_json(sbom), encoding="utf-8")
        provenance = build_container_release_provenance(
            image=image,
            tag=tag,
            digest=digest,
            repository=repository,
            commit=commit,
            workflow_run_url=workflow_run_url,
            sbom_path=sbom_path,
        )
        provenance_path.write_text(format_provenance_json(provenance), encoding="utf-8")
        click.echo(_ok(f"Container SBOM written: {sbom_path}"))
        click.echo(_ok(f"Container provenance written: {provenance_path}"))
    except Exception as exc:
        click.echo(_err(str(exc)), err=True)
        raise SystemExit(1)


@supply_chain.command("verify-container-release")
@click.option(
    "--provenance",
    required=True,
    help="Path to container-provenance.json generated by supply-chain container-release.",
)
@click.option("--sbom", default=None, help="Optional path to the container SBOM JSON.")
@click.option("--image", default="", help="Expected container image name.")
@click.option("--tag", default="", help="Expected release tag.")
@click.option("--digest", default="", help="Expected immutable image digest, sha256:<hex>.")
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["text", "json"]),
    default="text",
    show_default=True,
)
def supply_chain_verify_container_release(
    provenance: str,
    sbom: str | None,
    image: str,
    tag: str,
    digest: str,
    output_format: str,
):
    """Verify local container release provenance before trusting a release."""
    from skills_orchestrator.supply_chain import (
        format_container_release_verification,
        verify_container_release,
    )

    try:
        report = verify_container_release(
            provenance_path=provenance,
            sbom_path=sbom,
            expected_image=image,
            expected_tag=tag,
            expected_digest=digest,
        )
        if output_format == "json":
            click.echo(console_safe_text(format_container_release_verification(report)), nl=False)
        else:
            click.echo(f"Container release verification: {report['status']}")
            click.echo(
                f"Summary: {report['summary']['passed']} passed, {report['summary']['failed']} failed"
            )
            for check in report["checks"]:
                marker = "OK" if check["status"] == "pass" else "FAIL"
                click.echo(f"  [{marker}] {check['id']}")
        if report["status"] != "pass":
            raise SystemExit(1)
    except SystemExit:
        raise
    except Exception as exc:
        click.echo(_err(str(exc)), err=True)
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
                lines.append(f"门禁要求: 产出 '{step.gate.artifact_label()}'")
                if step.gate.min_length:
                    lines.append(f"  最小长度: {step.gate.min_length} 字符")

        if state.context:
            lines.append("")
            lines.append(f"上下文键: {', '.join(state.context.keys())}")

        click.echo(console_safe_text("\n".join(lines)))
    except Exception as e:
        click.echo(_err(str(e)), err=True)
        raise SystemExit(1)


@pipeline.command("list-runs")
@click.argument("pipeline_id", required=False, default=None)
@click.option("--limit", default=20, show_default=True, help="最多显示多少条运行记录")
@click.option("--json", "as_json", is_flag=True, help="输出 JSON，便于 Agent/CI 读取")
def pipeline_list_runs(pipeline_id: Optional[str], limit: int, as_json: bool):
    """列出 Pipeline 运行记录

    \b
    示例：
      skills-orchestrator pipeline list-runs
      skills-orchestrator pipeline list-runs quick-fix
      skills-orchestrator pipeline list-runs --json
    """
    from skills_orchestrator.pipeline.store import RunStateStore

    try:
        store = RunStateStore()
        rows = store.list_runs(pipeline_id)
        rows.sort(key=lambda row: row.get("updated_at") or "", reverse=True)
        rows = rows[: max(limit, 0)]

        if as_json:
            click.echo(json.dumps({"runs": rows}, ensure_ascii=False, indent=2))
            return

        if not rows:
            if pipeline_id:
                click.echo(_warn(f"没有找到 Pipeline '{pipeline_id}' 的运行记录。"))
            else:
                click.echo(_warn("没有找到 Pipeline 运行记录。"))
            return

        click.echo(f"\nPipeline 运行记录（{len(rows)} 条）：\n")
        for row in rows:
            current_step = row.get("current_step") or "(已完成)"
            click.echo(
                console_safe_text(
                    f"  {click.style(row['pipeline_id'], bold=True)} "
                    f"run={row['run_id']} status={row['status']} current={current_step}"
                )
            )
            click.echo(f"    started: {row['started_at']}")
            click.echo(f"    updated: {row['updated_at']}")
            click.echo("")
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
            lines.append(f"⚠ 门禁要求: 完成此步骤前必须产出 '{step.gate.artifact_label()}'")
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
