"""Generate small integration scaffolds for adjacent agent runtimes."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from skills_orchestrator.compiler import Parser
from skills_orchestrator.models import SkillMeta


def generate_mcp_client_config(config_path: str, *, zone: str | None = None) -> dict:
    """Return a stdio MCP client config for skills-orchestrator."""
    args = ["serve", "--config", str(Path(config_path).resolve())]
    if zone:
        args.extend(["--zone", zone])
    return {
        "mcpServers": {
            "skills-orchestrator": {
                "command": "skills-orchestrator",
                "args": args,
            }
        }
    }


def format_mcp_client_config(config: dict) -> str:
    """Render an MCP client config as JSON."""
    return json.dumps(config, ensure_ascii=False, indent=2) + "\n"


def generate_openai_agents_sdk_scaffold(config_path: str, *, zone: str | None = None) -> str:
    """Return a Python scaffold for attaching the MCP server to OpenAI Agents SDK."""
    args = ["serve", "--config", str(Path(config_path).resolve())]
    if zone:
        args.extend(["--zone", zone])
    args_repr = json.dumps(args, ensure_ascii=False)
    return f'''"""OpenAI Agents SDK scaffold for Skills Orchestrator MCP.

Install runtime dependencies separately:
    pip install openai-agents skills-orchestrator

This file constructs an Agent with the local skills-orchestrator stdio MCP server.
It does not call a model by itself.
"""

from agents import Agent
from agents.mcp import MCPServerStdio


server = MCPServerStdio(
    params={{
        "command": "skills-orchestrator",
        "args": {args_repr},
    }}
)

agent = Agent(
    name="SkillOps governed agent",
    instructions="Use Skills Orchestrator MCP tools to request task-scoped skills.",
    mcp_servers=[server],
)
'''


def export_claude_skill_bundles(
    config_path: str,
    output_dir: str | Path,
    *,
    force: bool = False,
) -> dict[str, Any]:
    """Export SkillOps skills as Claude-style */SKILL.md bundles."""
    cfg = Parser(config_path).parse()
    root = Path(output_dir)
    exported: list[dict[str, str]] = []
    for skill in cfg.skills:
        source_path = _skill_source_path(cfg.base_dir, skill.path)
        body = _strip_frontmatter(source_path.read_text(encoding="utf-8"))
        target_dir = root / skill.id
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / "SKILL.md"
        if target.exists() and not force:
            raise FileExistsError(f"Claude Skill already exists: {target}")
        target.write_text(_render_claude_skill(skill, body), encoding="utf-8")
        exported.append(
            {
                "id": skill.id,
                "source": str(source_path),
                "path": str(target),
            }
        )
    return {
        "schema_version": "skills-orchestrator.claude-skills-export.v1",
        "config": str(Path(config_path).resolve()),
        "output_dir": str(root.resolve()),
        "summary": {"exported": len(exported)},
        "skills": exported,
    }


def format_claude_skills_export_manifest(payload: dict[str, Any]) -> str:
    """Render Claude Skills export manifest JSON."""
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def _render_claude_skill(skill: SkillMeta, body: str) -> str:
    metadata: dict[str, Any] = {
        "id": skill.id,
        "name": skill.name,
        "description": skill.summary,
        "summary": skill.summary,
        "tags": skill.tags,
        "load_policy": skill.load_policy,
        "priority": skill.priority,
        "zones": skill.zones,
        "conflict_with": skill.conflict_with,
        "owner": skill.owner,
        "source": skill.source,
        "version": skill.version,
        "lifecycle": skill.lifecycle,
        "approvers": skill.approvers,
        "reviewed_at": skill.reviewed_at,
        "expires_at": skill.expires_at,
        "license": skill.license,
        "provenance": skill.provenance,
    }
    if skill.base:
        metadata["base"] = skill.base
    frontmatter = yaml.safe_dump(
        _drop_empty_metadata(metadata),
        allow_unicode=True,
        sort_keys=False,
    )
    return f"---\n{frontmatter}---\n\n{body.lstrip()}"


def _drop_empty_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in metadata.items() if value not in ("", [], {}, None)}


def _skill_source_path(base_dir: str, skill_path: str) -> Path:
    path = Path(skill_path)
    if path.is_absolute():
        return path
    return Path(base_dir) / path


def _strip_frontmatter(content: str) -> str:
    if not content.startswith("---"):
        return content
    end = content.find("\n---", 3)
    if end == -1:
        return content
    return content[end + len("\n---") :].lstrip("\n")
