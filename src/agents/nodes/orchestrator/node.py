from __future__ import annotations

from pathlib import Path

from agents.graph.states import State
from agents.model.gateway import MissingAPIKeyError, ModelGateway, get_default_gateway
from json_utils import extract_json
from prompting import render_prompt

_DIR = Path(__file__).parent
SYSTEM_PROMPT = (_DIR / "prompts" / "system.txt").read_text()
PROMPT_PATH = _DIR / "prompts" / "prompt.jinja"


async def orchestrator_node(state: State, gateway: ModelGateway | None = None) -> dict:
    query = state["query"]
    gateway = gateway or get_default_gateway()

    try:
        user_prompt = render_prompt(PROMPT_PATH, query=query)
        raw = await gateway.complete("orchestrator", system=SYSTEM_PROMPT, user=user_prompt)
        result = extract_json(raw)
        flagged = bool(result["flagged"])
    except MissingAPIKeyError:
        flagged = "urgent" in query.lower()

    return {
        "flagged": flagged,
        "status": "needs_review" if flagged else "running",
    }
