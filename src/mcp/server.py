"""MCP Skills Server 主入口"""

from __future__ import annotations

import logging

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types

from .registry import SkillRegistry
from .tools import ALL_TOOLS, ToolExecutor

logger = logging.getLogger(__name__)


def create_server(config_path: str) -> tuple[Server, ToolExecutor]:
    """创建并配置 MCP Server，返回 (server, executor)"""
    registry = SkillRegistry(config_path)
    executor = ToolExecutor(registry)

    server = Server("skills-orchestrator")

    @server.list_tools()
    async def list_tools() -> list[types.Tool]:
        return ALL_TOOLS

    @server.call_tool()
    async def call_tool(
        name: str, arguments: dict
    ) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
        logger.debug(f"call_tool: {name}({arguments})")
        return executor.execute(name, arguments or {})

    return server, executor


async def run_stdio(config_path: str) -> None:
    """以 stdio 模式运行 MCP Server（Claude Code 默认连接方式）"""
    server, _ = create_server(config_path)

    async with stdio_server() as (read_stream, write_stream):
        init_options = server.create_initialization_options()
        await server.run(read_stream, write_stream, init_options)
