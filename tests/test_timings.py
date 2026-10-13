import asyncio
from datetime import datetime

import pytest

from agents.graph.build import build_graph, timed


def test_a_timed_node_keeps_its_update_and_records_one_timing():
    async def node(state):
        await asyncio.sleep(0.01)
        return {"steps": [{"title": "Planned 2 steps"}]}

    update = asyncio.run(timed("planner", node)({}))

    assert update["steps"] == [{"title": "Planned 2 steps"}]
    [timing] = update["timings"]
    assert timing["agent"] == "planner"
    started = datetime.fromisoformat(timing["started_at"])
    finished = datetime.fromisoformat(timing["finished_at"])
    assert (finished - started).total_seconds() >= 0.01


def test_a_failed_call_records_no_timing():
    async def node(state):
        raise ValueError("no JSON in the answer")

    with pytest.raises(ValueError):
        asyncio.run(timed("planner", node)({}))


def test_the_graph_still_builds_with_timed_nodes():
    graph = build_graph("memory")
    assert {"orchestrator", "planner", "execution", "fetch", "review"} <= set(graph.nodes)
