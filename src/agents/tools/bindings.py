"""Lets an LLM node call MCP tools itself (Claude tool use).

Every tool the MCP server exposes is listed and passed to Claude as
`tools=[...]`; Claude decides which one fits the query. When Claude answers
with a `tool_use` block, the call goes through call_mcp_tool and the result
is sent back as a `tool_result`, until Claude gives a final text answer.
"""

from __future__ import annotations

import json
import logging
from contextlib import AsyncExitStack

from agents.model.gateway import ModelGateway
from agents.tools.mcp_client import call_mcp_tool, list_mcp_tools, mcp_client

logger = logging.getLogger(__name__)

MAX_ROUNDS = 5


async def complete_with_mcp_tools(
    node: str, system: str, user: str, gateway: ModelGateway
) -> tuple[str, list[dict]]:
    """Return (final text, MCP calls). Calls are kept so later nodes can use the data."""
    client = gateway.require_client()
    tool_results: list[dict] = []

    async with AsyncExitStack() as stack:
        try:
            mcp = await stack.enter_async_context(mcp_client(node))
            tools = await list_mcp_tools(mcp)
        except Exception as exc:
            logger.warning("[%s] MCP tool listing failed (%s) — running without tools", node, exc)
            tools = []
        if not tools:
            return await gateway.complete(node, system=system, user=user), tool_results

        logger.info(
            "[%s] offering MCP tools: %s",
            node,
            {t["name"]: sorted(t["tags"]) for t in tools},
        )
        claude_tools = [
            {"name": t["name"], "description": t["description"], "input_schema": t["input_schema"]}
            for t in tools
        ]
        config = gateway.policy.get(node, gateway.policy["default"])
        messages: list[dict] = [{"role": "user", "content": user}]

        for _ in range(MAX_ROUNDS):
            response = await client.messages.create(
                model=config["model"],
                max_tokens=config.get("max_tokens", 1024),
                system=system,
                messages=messages,
                tools=claude_tools,
            )
            if response.stop_reason != "tool_use":
                text = "".join(b.text for b in response.content if b.type == "text")
                return text, tool_results

            messages.append({"role": "assistant", "content": response.content})
            results = []
            for block in response.content:
                if block.type != "tool_use":
                    continue
                logger.info("[%s] model called MCP tool %s(%s)", node, block.name, block.input)
                try:
                    data = await call_mcp_tool(mcp, block.name, **block.input)
                    content = data if isinstance(data, str) else json.dumps(data)
                    results.append({"type": "tool_result", "tool_use_id": block.id, "content": content})
                    tool_results.append({"tool": block.name, "input": block.input, "result": content})
                except Exception as exc:
                    logger.warning("[%s] MCP tool %s failed: %s", node, block.name, exc)
                    results.append(
                        {"type": "tool_result", "tool_use_id": block.id, "content": str(exc), "is_error": True}
                    )
                    tool_results.append(
                        {"tool": block.name, "input": block.input, "result": str(exc), "error": True}
                    )
            messages.append({"role": "user", "content": results})

    raise RuntimeError(f"[{node}] tool loop did not finish within {MAX_ROUNDS} rounds")
