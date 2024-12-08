from __future__ import annotations

import asyncio
import inspect
import logging
import typing as t
from collections.abc import Sequence
from functools import cache

from mcp.server import Server
from mcp.types import (
    EmbeddedResource,
    ImageContent,
    TextContent,
    Tool,
)

from . import tools

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
app = Server("mcp-telegram")


@cache
def enumerate_available_tools() -> t.Generator[tuple[str, Tool], t.Any, None]:
    for _, obj in inspect.getmembers(tools, inspect.isclass):
        if issubclass(obj, tools.ToolArgs) and obj != tools.ToolArgs:
            logger.debug("Found tool: %s", obj)
            tool_args = obj()
            description = tools.tool_description(tool_args)
            yield description.name, description


mapping: dict[str, Tool] = dict(enumerate_available_tools())


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools."""
    return list(mapping.values())


@app.call_tool()
async def call_tool(name: str, arguments: t.Any) -> Sequence[TextContent | ImageContent | EmbeddedResource]:  # noqa: ANN401
    """Handle tool calls for command line run."""

    if not isinstance(arguments, dict):
        raise TypeError("arguments must be dictionary")

    tool = mapping.get(name)
    if not tool:
        raise ValueError(f"Unknown tool: {name}")

    try:
        args = tools.tool_args(tool, **arguments)
        return await tools.tool_runner(args)
    except Exception as e:
        logger.exception("Error running tool: %s", name)
        raise RuntimeError(f"Caught Exception. Error: {e}") from e


async def run_mcp_server() -> None:
    # Import here to avoid issues with event loops
    from mcp.server.stdio import stdio_server

    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


def main() -> None:
    asyncio.run(run_mcp_server())