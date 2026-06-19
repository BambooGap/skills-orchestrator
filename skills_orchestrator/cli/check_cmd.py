"""check command — structured skill diagnostics for local and CI use."""

from __future__ import annotations

import click

from skills_orchestrator.checker import DEFAULT_MAX_SKILL_BYTES, fatal_error_report, run_check
from skills_orchestrator.diagnostic import DiagnosticReport, DiagnosticSeverity
from skills_orchestrator.formatters import (
    format_diagnostics_json,
    format_diagnostics_sarif,
    format_diagnostics_text,
)
from skills_orchestrator.security import console_safe_text


@click.command("check")
@click.option("--config", "-c", default="config/skills.yaml", help="配置文件路径")
@click.option("--zone", "-z", default=None, help="指定 Zone ID，不传则使用 default zone")
@click.option("--check-lock", default=None, help="检查 skills.lock.json 是否过期")
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["text", "json", "sarif"]),
    default="text",
    show_default=True,
    help="输出格式",
)
@click.option(
    "--fail-on",
    type=click.Choice(["error", "warning", "never"]),
    default="error",
    show_default=True,
    help="达到指定严重级别时返回非零退出码",
)
@click.option(
    "--max-skill-bytes",
    default=DEFAULT_MAX_SKILL_BYTES,
    show_default=True,
    help="超过该字节数的 skill 标记为 oversized",
)
def check(
    config: str,
    zone: str | None,
    check_lock: str | None,
    output_format: str,
    fail_on: str,
    max_skill_bytes: int,
):
    """检查 skill 元数据、冲突声明和可选 lock 差异。"""
    try:
        report = run_check(
            config,
            zone_id=zone,
            check_lock=check_lock,
            max_skill_bytes=max_skill_bytes,
        )
    except Exception as exc:
        if output_format != "text":
            report = fatal_error_report(str(exc), config_path=config)
            click.echo(console_safe_text(_format_report(report, output_format)), nl=False)
            raise SystemExit(1)
        click.echo(console_safe_text(f"✗ {exc}"), err=True)
        raise SystemExit(1)

    click.echo(console_safe_text(_format_report(report, output_format)), nl=False)
    if _should_fail(report, fail_on, check_lock=check_lock is not None):
        raise SystemExit(1)


def _format_report(report: DiagnosticReport, output_format: str) -> str:
    if output_format == "json":
        return format_diagnostics_json(report)
    if output_format == "sarif":
        return format_diagnostics_sarif(report)
    return format_diagnostics_text(report)


def _should_fail(report: DiagnosticReport, fail_on: str, *, check_lock: bool = False) -> bool:
    if fail_on == "never":
        return False
    if check_lock and any(diagnostic.rule_id == "SO007" for diagnostic in report.diagnostics):
        return True
    if fail_on == "warning":
        return any(
            diagnostic.severity in (DiagnosticSeverity.ERROR, DiagnosticSeverity.WARNING)
            for diagnostic in report.diagnostics
        )
    return any(diagnostic.severity == DiagnosticSeverity.ERROR for diagnostic in report.diagnostics)
