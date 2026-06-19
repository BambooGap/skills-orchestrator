"""policy command — export resolver facts for policy-as-code tools."""

from __future__ import annotations

import json
from pathlib import Path

import click

from skills_orchestrator.compiler import Parser, Resolver
from skills_orchestrator.policy import build_opa_input, build_rego_test
from skills_orchestrator.security import console_safe_text


@click.group("policy")
def policy():
    """Policy-as-code export helpers."""
    pass


@policy.command("export")
@click.option("--config", "-c", default="config/skills.yaml", help="配置文件路径")
@click.option("--zone", "-z", default=None, help="指定 Zone ID，不传则使用 default zone")
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["opa-input", "rego-test"]),
    default="opa-input",
    show_default=True,
    help="输出格式",
)
@click.option("--output", "-o", default="-", help="输出路径；默认 '-' 表示 stdout")
@click.option(
    "--package",
    "rego_package",
    default="skills_orchestrator_test",
    show_default=True,
    help="rego-test 输出使用的 Rego package",
)
def export(config: str, zone: str | None, output_format: str, output: str, rego_package: str):
    """导出 OPA input 或 Rego 测试 fixture，不启用 OPA runtime backend。"""
    try:
        parser = Parser(config)
        cfg = parser.parse()
        target_zone = _select_zone(cfg, zone)
        resolved = Resolver(cfg).resolve(target_zone)
        payload = build_opa_input(cfg, resolved)
        if output_format == "rego-test":
            rendered = build_rego_test(payload, package=rego_package)
        else:
            rendered = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
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


def _write_output(content: str, output: str) -> None:
    if output == "-":
        click.echo(console_safe_text(content), nl=False)
        return
    Path(output).write_text(content, encoding="utf-8")
