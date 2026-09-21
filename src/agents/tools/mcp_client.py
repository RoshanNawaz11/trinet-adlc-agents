"""Agent-side MCP client — connects to the dummy MCP servers in mcp_server/
(agents_server.py, and the MCP tools graphql_server.py auto-derives from its
GraphQL schema) and calls a tool on behalf of a given node.

Uses `fastmcp.Client` rather than the raw `mcp` SDK since it's already what
`graphql_mcp`/our servers are built on — same library, client side.
"""

from __future__ import annotations

import json
from typing import Any

from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport

from agents.tools.scopes import MCP_SERVERS, assert_mcp_allowed

NODE_HEADER = "x-agent-node"


def mcp_client(url: str, node: str | None = None) -> Client:
    """HTTP MCP client. `node` is sent as x-agent-node so the server can scope the call."""
    headers = {NODE_HEADER: node} if node else None
    if headers:
        return Client(StreamableHttpTransport(url, headers=headers))
    return Client(url)


async def call_mcp_tool(node: str, server: str, tool_name: str, **kwargs: Any) -> Any:
    """Call `tool_name` on `server` (a key in MCP_SERVERS) as `node`.

    Raises ScopeError if `node` isn't scoped to call this tool, or
    ConnectionError-style exceptions from fastmcp if the server isn't running
    — callers decide whether that's fatal or something to fall back on.
    """
    assert_mcp_allowed(node, server, tool_name)
    url = MCP_SERVERS[server]

    async with mcp_client(url, node) as client:
        result = await client.call_tool(tool_name, kwargs)

    data = result.data
    if isinstance(data, str):
        try:
            return json.loads(data)
        except json.JSONDecodeError:
            return data
    return data
