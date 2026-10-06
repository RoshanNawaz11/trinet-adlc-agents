"""Execution Agent — fetch mode. The only way any agent gets data from an
external system: the orchestrator hands it the open needs addressed to
"execution", and the model answers them with the MCP server's read-only tools.

The tools are discovered from the server each time, never named here; the
server's read-only annotation is the one thing enforced in code, so fetching
can never write. Write tools belong to the final execution, after review.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from agents.graph.states import Need, State, step_record
from agents.model.gateway import ModelGateway, get_default_gateway
from agents.tools.bindings import complete_with_mcp_tools
from json_utils import JSONParseError, extract_json

logger = logging.getLogger(__name__)

_INSTRUCTION = (
    "You fetch data for other agents. Each need below asks for some data in plain text. "
    "Use the tools to answer every need. Return only facts the tools returned — never "
    "invent or guess a value. Never guess an id (rule id, employee id, …) to probe a "
    "tool: use only ids that appear in the need or that a tool returned. If no tool can "
    "answer a need, or the tool finds nothing, mark it failed and say why. "
    'Your final answer must be a single JSON object: {"answers": [{"id": "<need id>", '
    '"status": "done" | "failed", "answer": {<the data>} or null, "error": "<why it failed>" or null}]}. '
    "Return ONLY JSON — no preamble, no markdown fences."
)


def open_fetch_needs(state: State) -> list[Need]:
    return [n for n in state.get("needs") or [] if n["ask"] == "execution" and n["status"] == "open"]


def _failed(need: Need, error: str) -> Need:
    return {**need, "status": "failed", "answer": None, "error": error}


async def fetch_node(state: State, gateway: ModelGateway | None = None) -> dict[str, Any]:
    needs = open_fetch_needs(state)
    if not needs:
        return {}
    gateway = gateway or get_default_gateway()
    logger.info("[execution:fetch] answering %s", [n["id"] for n in needs])

    request = json.dumps(
        [{"id": n["id"], "request": n["request"], "args": n["args"]} for n in needs],
        indent=2, default=str, ensure_ascii=False,
    )
    raw, calls = await complete_with_mcp_tools(
        "execution", _INSTRUCTION, request, gateway, read_only=True,
    )

    answers: dict[str, dict] = {}
    if raw:
        try:
            parsed = extract_json(raw, key="answers")
            answers = {a["id"]: a for a in parsed["answers"] if isinstance(a, dict) and "id" in a}
        except (JSONParseError, KeyError, TypeError) as exc:
            logger.warning("[execution:fetch] unreadable answer (%s): %r", exc, raw[:500])

    updated: list[Need] = []
    for need in needs:
        a = answers.get(need["id"])
        if not raw:
            updated.append(_failed(need, "No read-only MCP tools available"))
        elif a is None:
            updated.append(_failed(need, "Fetch returned no answer for this need"))
        elif a.get("status") == "done":
            updated.append({**need, "status": "done", "answer": a.get("answer"), "error": None})
        else:
            updated.append(_failed(need, str(a.get("error") or "Not found")))

    # a lookup belongs to the stage of whoever asked for it, not to Distribution Info
    asker = needs[0]["from_agent"]
    stage = "payroll" if asker == "payroll-calculation" else asker
    steps = [
        step_record(
            stage, "Execution Agent (fetch)", f"Looked up {call['tool']}", f"MCP · {call['tool']}",
            result="error" if call.get("error") else "ok", evidence=call["input"], at=call["at"],
        )
        for call in calls
    ]
    logger.info("[execution:fetch] done: %s", {n["id"]: n["status"] for n in updated})
    return {"needs": updated, "steps": steps}
