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
from agents.skills.client import CODE_EXECUTION_TOOL, MAX_TOKENS, run_skill
from agents.tools.mcp_client import call_mcp_tool, list_mcp_tools, mcp_client
from agents.tools.scopes import MCP_SERVER

logger = logging.getLogger(__name__)

MAX_ROUNDS = 5


async def complete_with_mcp_tools(
    node: str,
    system: str,
    user: str,
    gateway: ModelGateway,
    skill: tuple[str, str] | None = None,
    *,
    read_only: bool = False,
) -> tuple[str, list[dict]]:
    """Return (final text, MCP calls). Calls are kept so later nodes can use the data.

    `skill` is the (skill_id, version_id) from ensure_bundle_published; when
    given, it is attached to every model call alongside the MCP tools.
    `read_only` offers only the tools the server annotates as read-only.
    Without a skill and without tools there is nothing to run: returns ("", []).
    """
    config = gateway.policy.get(node, gateway.policy["default"])

    async def without_tools() -> tuple[str, list[dict]]:
        if skill is None:
            return "", []
        executed = await run_skill(
            *skill, user,
            model=config["model"], additional_instructions=system, gateway=gateway,
        )
        return executed["raw_response"], []

    if not MCP_SERVER:
        return await without_tools()
    client = gateway.require_client()
    tool_results: list[dict] = []

    async with AsyncExitStack() as stack:
        try:
            mcp = await stack.enter_async_context(mcp_client(node))
            tools = await list_mcp_tools(mcp)
        except Exception as exc:
            logger.warning("[%s] MCP tool listing failed (%s) — running without tools", node, exc)
            tools = []
        if read_only:
            tools = [t for t in tools if t["read_only"]]
        if not tools:
            return await without_tools()

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
        with_skill: dict = {}
        if skill is not None:
            skill_id, version_id = skill
            with_skill = {
                "container": {"skills": [{"type": "custom", "skill_id": skill_id, "version": version_id}]},
            }
            claude_tools.append(CODE_EXECUTION_TOOL)

        for _ in range(MAX_ROUNDS):
            response = await client.messages.create(
                model=config["model"],
                # skills + code execution need room; 1024 cut answers off mid-work
                max_tokens=config.get("max_tokens", MAX_TOKENS),
                system=system,
                messages=messages,
                tools=claude_tools,
                **with_skill,
            )
            if response.stop_reason == "pause_turn":
                # the skill's code execution paused a long turn; send it back to continue
                messages.append({"role": "assistant", "content": response.content})
                continue
            if response.stop_reason != "tool_use":
                logger.info("[%s] model finished: stop_reason=%s", node, response.stop_reason)
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

        # Out of rounds: one last call with tools switched off, so the model
        # answers with what it found (and says what it couldn't) instead of
        # the whole run failing.
        logger.warning("[%s] tool loop hit %d rounds — asking for a final answer without tools", node, MAX_ROUNDS)
        if messages[-1]["role"] == "user":
            messages[-1]["content"] = [*messages[-1]["content"], {
                "type": "text",
                "text": "No more tool calls. Give your final answer now from what the tools returned; "
                        "anything you couldn't find is not available.",
            }]
        response = await client.messages.create(
            model=config["model"],
            max_tokens=config.get("max_tokens", MAX_TOKENS),
            system=system,
            messages=messages,
            tools=claude_tools,
            tool_choice={"type": "none"},
            **with_skill,
        )
        logger.info("[%s] model finished after the round limit: stop_reason=%s", node, response.stop_reason)
        return "".join(b.text for b in response.content if b.type == "text"), tool_results
