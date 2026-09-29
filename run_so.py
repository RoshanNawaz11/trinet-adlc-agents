"""Run the agents on one service order. Set SO_ID below, then:

    uv run run_so.py

The order is fetched through the MCP server (MCP_SERVER in .env), so the MCP
and GraphQL services must be running. The full result is printed and logged
to logs/agents.log.
"""

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from agents.observability.langwatch_setup import langwatch_setup
from agents.runtime.runner import _setup_logging, run_query

SO_ID = "SO-1003"


async def main() -> None:
    _setup_logging()
    langwatch_setup()
    out = await run_query(service_order_id=SO_ID)
    print(json.dumps(out, default=str, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
