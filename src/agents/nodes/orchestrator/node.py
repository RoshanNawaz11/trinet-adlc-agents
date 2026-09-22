from __future__ import annotations

import logging
from pathlib import Path

from agents.graph.states import State
from agents.model.gateway import MissingAPIKeyError, ModelGateway, get_default_gateway
from agents.tools.bindings import complete_with_mcp_tools
from json_utils import JSONParseError, extract_json
from prompting import render_prompt

logger = logging.getLogger(__name__)

_DIR = Path(__file__).parent
SYSTEM_PROMPT = (_DIR / "prompts" / "system.txt").read_text()
PROMPT_PATH = _DIR / "prompts" / "prompt.jinja"


async def orchestrator_node(state: State, gateway: ModelGateway | None = None) -> dict:
    query = state["query"]
    gateway = gateway or get_default_gateway()
    logger.info("orchestrator_node starting for query=%r", query[:100])

    mcp_results: list = []
    try:
        user_prompt = render_prompt(PROMPT_PATH, query=query)
        raw, mcp_results = await complete_with_mcp_tools(
            "orchestrator", "agents", system=SYSTEM_PROMPT, user=user_prompt, gateway=gateway
        )
        result = extract_json(raw)
        flagged = bool(result["flagged"])
        logger.info("orchestrator_node: model result=%s mcp_calls=%d", result, len(mcp_results))
    except JSONParseError:
        logger.exception("orchestrator_node: could not parse model output: %r", raw)
        raise
    except MissingAPIKeyError:
        flagged = "urgent" in query.lower()
        logger.warning(
            "orchestrator_node: no credentials configured — falling back to "
            "keyword check, flagged=%s", flagged,
        )

    logger.info("orchestrator_node done: flagged=%s", flagged)
    return {
        "flagged": flagged,
        "status": "needs_review" if flagged else "running",
        "mcp_results": mcp_results,
    }
