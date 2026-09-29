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
from datetime import UTC, datetime

from agents.model.gateway import ModelGateway
from agents.skills.client import CODE_EXECUTION_TOOL, run_skill
from agents.tools.mcp_client import call_mcp_tool, list_mcp_tools, mcp_client
from agents.tools.scopes import MCP_SERVER

logger = logging.getLogger(__name__)

MAX_ROUNDS = 5


async def complete_with_mcp_tools(
    node: str, system: str, user: str, gateway: ModelGateway, skill: tuple[str, str]
) -> tuple[str, list[dict]]:
    """Return (final text, MCP calls). Calls are kept so later nodes can use the data.

    `skill` is the (skill_id, version_id) from ensure_bundle_published; it is
    attached to every model call alongside the MCP tools.
    """
    skill_id, version_id = skill
    config = gateway.policy.get(node, gateway.policy["default"])
    if not MCP_SERVER:
        executed = await run_skill(
            skill_id, version_id, user,
            model=config["model"], additional_instructions=system, gateway=gateway,
        )
        return executed["raw_response"], []
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
            executed = await run_skill(
                skill_id, version_id, user,
                model=config["model"], additional_instructions=system, gateway=gateway,
            )
            return executed["raw_response"], tool_results

        logger.info(
            "[%s] offering MCP tools: %s",
            node,
            {t["name"]: sorted(t["tags"]) for t in tools},
        )
        claude_tools = [
            {"name": t["name"], "description": t["description"], "input_schema": t["input_schema"]}
            for t in tools
        ]
        messages: list[dict] = [{"role": "user", "content": user}]

        for _ in range(MAX_ROUNDS):
            response = await client.messages.create(
                model=config["model"],
                max_tokens=config.get("max_tokens", 1024),
                system=system,
                messages=messages,
                container={"skills": [{"type": "custom", "skill_id": skill_id, "version": version_id}]},
                tools=[*claude_tools, CODE_EXECUTION_TOOL],
            )
            if response.stop_reason == "pause_turn":
                # the skill's code execution paused a long turn; send it back to continue
                messages.append({"role": "assistant", "content": response.content})
                continue
            if response.stop_reason != "tool_use":
                text = "".join(b.text for b in response.content if b.type == "text")
                return text, tool_results

            messages.append({"role": "assistant", "content": response.content})
            results = []
            for block in response.content:
                if block.type != "tool_use":
                    continue
                logger.info("[%s] model called MCP tool %s(%s)", node, block.name, block.input)
                at = datetime.now(UTC).isoformat()
                try:
                    data = await call_mcp_tool(mcp, block.name, **block.input)
                    content = data if isinstance(data, str) else json.dumps(data)
                    results.append({"type": "tool_result", "tool_use_id": block.id, "content": content})
                    tool_results.append({"tool": block.name, "input": block.input, "result": content, "at": at})
                except Exception as exc:
                    logger.warning("[%s] MCP tool %s failed: %s", node, block.name, exc)
                    results.append(
                        {"type": "tool_result", "tool_use_id": block.id, "content": str(exc), "is_error": True}
                    )
                    tool_results.append(
                        {"tool": block.name, "input": block.input, "result": str(exc), "error": True, "at": at}
                    )
            messages.append({"role": "user", "content": results})

    raise RuntimeError(f"[{node}] tool loop did not finish within {MAX_ROUNDS} rounds")
