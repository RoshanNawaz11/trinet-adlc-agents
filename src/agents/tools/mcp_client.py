"""Agent-side MCP client — connects to the server configured in scopes.py
"""

from __future__ import annotations

import json
from typing import Any

from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport

from agents.tools.scopes import MCP_SERVER

NODE_HEADER = "x-agent-node"  # header name is a protocol constant, not per-deployment config
DEFAULT_TIMEOUT = 30.0  # seconds — measured handshake is ~11s, so leave real headroom


def mcp_client(node: str | None = None) -> Client:
    """HTTP MCP client for MCP_SERVER. `node` is sent as x-agent-node for server-side logging/auditing."""
    headers = {NODE_HEADER: node} if node else None
    transport = StreamableHttpTransport(MCP_SERVER, headers=headers) if headers else MCP_SERVER
    return Client(transport, timeout=DEFAULT_TIMEOUT)


def tool_tags(tool: Any) -> set[str]:
    meta = tool.meta or {}
    return set(meta.get("fastmcp", {}).get("tags", []))


async def list_mcp_tools(client: Client) -> list[dict]:
    """Tools MCP_SERVER currently exposes, each with the tags the server put on it.

    `tags` rides alongside Claude's tool-schema fields, not inside them — the
    Anthropic API rejects unknown keys, so callers strip it before the call.
    """
    tools = await client.list_tools()
    return [
        {
            "name": t.name,
            "description": t.description or "",
            "input_schema": t.inputSchema,
            "tags": tool_tags(t),
        }
        for t in tools
    ]


async def call_mcp_tool(client: Client, tool_name: str, **kwargs: Any) -> Any:
    """Call `tool_name` on an already-open MCP client connection.

    Raises ConnectionError-style exceptions from fastmcp if the server isn't
    running — callers decide whether that's fatal or something to fall back on.
    """
    result = await client.call_tool(tool_name, kwargs)

    data = result.data
    if isinstance(data, str):
        try:
            return json.loads(data)
        except json.JSONDecodeError:
            return data
    return data
