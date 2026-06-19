"""manifest command — export instruction inventories."""

from __future__ import annotations

from pathlib import Path

import click

from skills_orchestrator.checker import run_check
from skills_orchestrator.compiler import Parser, Resolver
from skills_orchestrator.compiler.instruction_manifest import build_instruction_manifest
from skills_orchestrator.formatters import (
    format_instruction_manifest_cyclonedx,
    format_instruction_manifest_json,
)
from skills_orchestrator.security import console_safe_text


@click.command("manifest")
@click.option("--config", "-c", default="config/skills.yaml", help="配置文件路径")
@click.option("--zone", "-z", default=None, help="指定 Zone ID，不传则使用 default zone")
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["json", "cyclonedx"]),
    default="json",
    show_default=True,
    help="输出格式",
)
@click.option("--output", "-o", default="-", help="输出路径；默认 '-' 表示 stdout")
@click.option(
    "--include-diagnostics",
    is_flag=True,
    help="在 native JSON 中嵌入 check diagnostics 摘要",
)
def manifest(
    config: str, zone: str | None, output_format: str, output: str, include_diagnostics: bool
):
    """导出 instruction manifest 或实验性 CycloneDX BOM。"""
    try:
        parser = Parser(config)
        cfg = parser.parse()
        target_zone = _select_zone(cfg, zone)
        resolved = Resolver(cfg).resolve(target_zone)
        payload = build_instruction_manifest(config, cfg, resolved)
        if include_diagnostics:
            report = run_check(config, zone_id=zone)
            payload["diagnostics"] = {
                "summary": report.summary(),
                "items": [diagnostic.to_dict() for diagnostic in report.diagnostics],
            }
        rendered = _format_manifest(payload, output_format)
        _write_output(rendered, output)
    except Exception as exc:
        raise click.ClickException(str(exc)) from exc


def _select_zone(cfg, zone_id: str | None):
    if not zone_id:
        return None
    target_zone = next((zone for zone in cfg.zones if zone.id == zone_id), None)
    if not target_zone:
        raise ValueError(f"Zone '{zone_id}' 不存在")
    return target_zone


def _format_manifest(payload: dict, output_format: str) -> str:
    if output_format == "cyclonedx":
        return format_instruction_manifest_cyclonedx(payload)
    return format_instruction_manifest_json(payload)


def _write_output(content: str, output: str) -> None:
    if output == "-":
        click.echo(console_safe_text(content), nl=False)
        return
    Path(output).write_text(content, encoding="utf-8")
