"""Generate small integration scaffolds for adjacent agent runtimes."""

from __future__ import annotations

import json
from pathlib import Path


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
