"""Ecosystem adapter inspection and scaffold helpers."""

from .inspect import inspect_adapters
from .scaffolds import (
    export_claude_skill_bundles,
    format_claude_skills_export_manifest,
    generate_mcp_client_config,
    generate_openai_agents_sdk_scaffold,
)

__all__ = [
    "export_claude_skill_bundles",
    "format_claude_skills_export_manifest",
    "generate_mcp_client_config",
    "generate_openai_agents_sdk_scaffold",
    "inspect_adapters",
]
