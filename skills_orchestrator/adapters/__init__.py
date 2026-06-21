"""Ecosystem adapter inspection and scaffold helpers."""

from .inspect import inspect_adapters
from .scaffolds import generate_mcp_client_config, generate_openai_agents_sdk_scaffold

__all__ = [
    "generate_mcp_client_config",
    "generate_openai_agents_sdk_scaffold",
    "inspect_adapters",
]
