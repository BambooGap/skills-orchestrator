"""MCP Skills Server 主入口"""

from __future__ import annotations

import logging

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types

from .registry import SkillRegistry
from .tools import ALL_TOOLS, ToolExecutor

logger = logging.getLogger(__name__)


def create_server(
    config_path: str, zone_id: str | None = None, pipelines_dir: str | None = None
) -> tuple[Server, ToolExecutor]:
    """创建并配置 MCP Server，返回 (server, executor)

    Args:
        config_path: 配置文件路径
        zone_id: 指定的 zone id（可选）
        pipelines_dir: pipelines 目录路径（可选，用于外部项目）
    """
    registry = SkillRegistry(config_path, zone_id=zone_id)
    executor = ToolExecutor(registry, pipelines_dir=pipelines_dir)

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


async def run_stdio(
    config_path: str, zone_id: str | None = None, pipelines_dir: str | None = None
) -> None:
    """以 stdio 模式运行 MCP Server（Claude Code 默认连接方式）

    Args:
        config_path: 配置文件路径
        zone_id: 指定的 zone id（可选）
        pipelines_dir: pipelines 目录路径（可选）
    """
    server, _ = create_server(config_path, zone_id=zone_id, pipelines_dir=pipelines_dir)

    async with stdio_server() as (read_stream, write_stream):
        init_options = server.create_initialization_options()
        await server.run(read_stream, write_stream, init_options)
