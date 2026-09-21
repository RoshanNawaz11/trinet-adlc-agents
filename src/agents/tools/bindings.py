"""Lets an LLM node call MCP tools itself (Claude tool use).

The node's allowed tools (scopes.py) are listed from the MCP server and
passed to Claude as `tools=[...]`. When Claude answers with a `tool_use`
block, the call goes through call_mcp_tool (scope-checked) and the result is
sent back as a `tool_result`, until Claude gives a final text answer.
"""

from __future__ import annotations

import json
import logging

from agents.model.gateway import ModelGateway
from agents.tools.mcp_client import call_mcp_tool, mcp_client
from agents.tools.scopes import MCP_SERVERS, NODE_MCP_SCOPES

logger = logging.getLogger(__name__)

MAX_ROUNDS = 5


async def _allowed_tools(node: str, server: str) -> list[dict]:
    allowed = NODE_MCP_SCOPES.get(node, {}).get(server, set())
    if not allowed:
        return []
    async with mcp_client(MCP_SERVERS[server]) as client:
        tools = await client.list_tools()
    return [
        {"name": t.name, "description": t.description or "", "input_schema": t.inputSchema}
        for t in tools
        if t.name in allowed
    ]


async def complete_with_mcp_tools(
    node: str, server: str, system: str, user: str, gateway: ModelGateway
) -> str:
    client = gateway.require_client()

    try:
        tools = await _allowed_tools(node, server)
    except Exception as exc:
        logger.warning("[%s] could not list MCP tools on %r (%s) — running without tools", node, server, exc)
        tools = []
    if not tools:
        return await gateway.complete(node, system=system, user=user)

    logger.info("[%s] offering MCP tools: %s", node, [t["name"] for t in tools])
    config = gateway.policy.get(node, gateway.policy["default"])
    messages: list[dict] = [{"role": "user", "content": user}]

    for _ in range(MAX_ROUNDS):
        response = await client.messages.create(
            model=config["model"],
            max_tokens=config.get("max_tokens", 1024),
            system=system,
            messages=messages,
            tools=tools,
        )
        if response.stop_reason != "tool_use":
            return "".join(b.text for b in response.content if b.type == "text")

        messages.append({"role": "assistant", "content": response.content})
        results = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            logger.info("[%s] model called MCP tool %s(%s)", node, block.name, block.input)
            try:
                data = await call_mcp_tool(node, server, block.name, **block.input)
                content = data if isinstance(data, str) else json.dumps(data)
                results.append({"type": "tool_result", "tool_use_id": block.id, "content": content})
            except Exception as exc:
                logger.warning("[%s] MCP tool %s failed: %s", node, block.name, exc)
                results.append(
                    {"type": "tool_result", "tool_use_id": block.id, "content": str(exc), "is_error": True}
                )
        messages.append({"role": "user", "content": results})

    raise RuntimeError(f"[{node}] tool loop did not finish within {MAX_ROUNDS} rounds")
