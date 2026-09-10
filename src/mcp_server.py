"""
MCP server — the same tools, exposed to any Model Context Protocol client.

    python -m src.mcp_server            # stdio (Claude Desktop, IDEs)
    python -m src.mcp_server --http     # HTTP on KINETIC_MCP_HOST:KINETIC_MCP_PORT

The tool registry is the single source of truth, so anything the in-app agent
can do is available over MCP with the same descriptions and units.
"""

from __future__ import annotations

import sys

from fastmcp import FastMCP

import config
from src.tools import REGISTRY

server = FastMCP("kinetic-research")

for entry in REGISTRY.values():
    server.tool(name=entry.name, description=entry.description)(entry.run)


def main() -> None:
    if "--http" in sys.argv:
        server.run(transport="http", host=config.MCP_HOST, port=config.MCP_PORT)
    else:
        server.run(transport="stdio")


if __name__ == "__main__":
    main()
