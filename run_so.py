"""Run the agents on one service order. Set SO_ID below, then:

    uv run run_so.py

The order is fetched through the MCP server (MCP_SERVER in .env), so the MCP
and GraphQL services must be running. Once every agent has finished, the run
pauses for review: each agent's result and every flag are shown here, and you
approve (execution builds the package) or reject (the run ends). The full
result is printed and logged to logs/agents.log.
"""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from agents.observability.langwatch_setup import langwatch_setup
from agents.runtime.runner import _setup_logging, close_graph, run_query

SO_ID = "SO-1003"


def _ask(pending: dict) -> dict:
    """Show the whole run and read the reviewer's decision from the terminal."""
    print("\n" + "=" * 70)
    print(f"REVIEW  {pending.get('service_order_id')}")
    for agent, result in pending["results"].items():
        print(f"\n--- {agent} (confidence {result.get('confidence')})")
        print(json.dumps(result.get("cases", result), indent=2, default=str))
    flags = pending["flags"]
    print(f"\nFlags ({len(flags)}):" if flags else "\nFlags: none")
    for f in flags:
        print(f"  • {f['flag_id']} [{f['type']}] {f['title']}")
        print(f"      {json.dumps(f['detail'], default=str)}")
        rec = f.get("recommendation")
        print(f"      → on approve: {rec}" if rec else "      → nothing to apply: fix the data and run again")
    if pending.get("summary"):
        print(f"\nSummary: {pending['summary']}")
    while True:
        action = input("\n[a]pprove (execute) / [r]eject (stop)? ").strip().lower()
        if action in ("a", "approve"):
            return {"action": "approve"}
        if action in ("r", "reject"):
            while not (reason := input("reason (required): ").strip()):
                pass
            return {"action": "reject", "reason": reason}


async def main() -> None:
    _setup_logging()
    langwatch_setup()
    try:
        out = await run_query(service_order_id=SO_ID)
        while out.get("paused"):
            pending = out["values"]["__interrupt__"][0].value
            decision = await asyncio.to_thread(_ask, pending)
            out = await run_query(thread_id=out["thread_id"], resume=True, decision=decision)
    finally:
        await close_graph()
    print(json.dumps(out, default=str, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
