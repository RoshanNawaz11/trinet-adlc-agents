"""Runs one worker alone, with the real model, on the exact input it got in an
earlier run — the agent's "Worker <kind>" step in the run's checkpoint keeps
it. No other agent, MCP server or worker pool is needed, only the model gateway.

    RUN=2026-10-12_0822_SO-20261002-1002_ce5f1221 uv run pytest tests/test_worker_replay.py -s
    (KIND=payroll-calculation.leave by default)

Skipped unless RUN names a folder in logs/.
"""

import json
import os
import sqlite3
from pathlib import Path

import pytest

RUN = os.getenv("RUN")
KIND = os.getenv("KIND", "payroll-calculation.leave")
LOGS = Path(__file__).resolve().parents[1] / "logs"


@pytest.mark.asyncio
@pytest.mark.skipif(not RUN, reason="set RUN to a run folder in logs/ to replay a worker")
async def test_replay_worker():
    from agents.queue.pool import HANDLERS
    from agents.runtime.runner import open_graph

    with sqlite3.connect(LOGS / RUN / "checkpoint.db") as conn:
        thread_id = conn.execute("SELECT thread_id FROM checkpoints LIMIT 1").fetchone()[0]
    async with open_graph(thread_id) as graph:
        state = await graph.aget_state({"configurable": {"thread_id": thread_id}})
    inputs = [s["evidence"]["input"] for s in state.values.get("steps", []) if s["title"] == f"Worker {KIND}"]
    assert inputs, f"{KIND} didn't run in {RUN}"

    result = await HANDLERS[KIND](inputs[-1])
    print(json.dumps(result, indent=2, default=str))
    assert result["findings"].get("rules"), "no rule ran on the model's facts"
