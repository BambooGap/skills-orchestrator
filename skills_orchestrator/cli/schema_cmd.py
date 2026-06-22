"""schema command - validate config and artifact files against JSON Schema."""

from __future__ import annotations

import json

import click

from skills_orchestrator.schema_validation import (
    SCHEMAS,
    list_schema_descriptors,
    validate_document,
)
from skills_orchestrator.security import console_safe_text

from .helpers import _err, _ok


@click.group("schema")
def schema() -> None:
    """List and validate stable JSON Schema contracts."""


@schema.command("list")
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["text", "json"]),
    default="text",
    show_default=True,
)
def schema_list(output_format: str) -> None:
    """List available schema kinds."""
    descriptors = list_schema_descriptors()
    if output_format == "json":
        payload = {
            "schema_version": "skills-orchestrator.schema-catalog.v1",
            "schemas": [descriptor.to_catalog_entry() for descriptor in descriptors],
        }
        click.echo(json.dumps(payload, ensure_ascii=False, indent=2))
        return

    click.echo("Available schemas:")
    for descriptor in descriptors:
        click.echo(
            f"  {descriptor.kind}: {descriptor.title} "
            f"[{descriptor.stability}] ({descriptor.filename})"
        )


@schema.command("validate")
@click.option(
    "--kind",
    type=click.Choice(sorted(SCHEMAS)),
    required=True,
    help="Schema kind to validate against.",
)
@click.option(
    "--input",
    "input_path",
    type=click.Path(exists=True, dir_okay=False, readable=True),
    required=True,
    help="JSON or YAML file to validate.",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["text", "json"]),
    default="text",
    show_default=True,
)
def schema_validate(kind: str, input_path: str, output_format: str) -> None:
    """Validate one file against a registered schema."""
    try:
        result = validate_document(kind, input_path)
    except Exception as exc:
        if output_format == "json":
            payload = {
                "schema_version": "skills-orchestrator.schema-validation.v1",
                "kind": kind,
                "input": input_path,
                "valid": False,
                "errors": [{"path": "$", "message": str(exc), "schema_path": "$"}],
            }
            click.echo(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            click.echo(_err(str(exc)), err=True)
        raise SystemExit(1) from exc

    if output_format == "json":
        click.echo(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    elif result.valid:
        click.echo(_ok(f"Schema valid: {kind} {input_path}"))
    else:
        click.echo(_err(f"Schema invalid: {kind} {input_path}"))
        for issue in result.errors:
            click.echo(console_safe_text(f"  {issue.path}: {issue.message}"))

    if not result.valid:
        raise SystemExit(1)
