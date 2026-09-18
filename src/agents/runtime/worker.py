"""Process entrypoint: build the compiled graph and invoke/resume it.

This is the runtime worker (queue consumer / CLI), not nodes/worker
(the classify skill node).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import uuid
from typing import Any

from agents.graph.build import build_graph
from agents.runtime.idempotency import already_processed, idempotency_key, mark_processed

_graph = None


def get_graph():
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph


def _initial_state(query: str, run_id: str) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "run_id": run_id,
        "query": query,
        "status": "running",
        "flagged": False,
        "step_results": [],
    }


def _config(thread_id: str) -> dict[str, Any]:
    return {"configurable": {"thread_id": thread_id}}


async def run_query(
    query: str,
    *,
    thread_id: str | None = None,
    resume: bool = False,
) -> dict[str, Any]:
    graph = get_graph()
    thread_id = thread_id or str(uuid.uuid4())
    config = _config(thread_id)
    key = idempotency_key(f"{thread_id}:{query}")

    if not resume and already_processed(key):
        snapshot = await graph.aget_state(config)
        return {
            "thread_id": thread_id,
            "skipped": True,
            "reason": "idempotent replay",
            "values": snapshot.values,
        }

    if resume:
        result = await graph.ainvoke(None, config)
    else:
        result = await graph.ainvoke(_initial_state(query, thread_id), config)

    snapshot = await graph.aget_state(config)
    paused = bool(snapshot.next)
    if not paused:
        mark_processed(key)

    return {
        "thread_id": thread_id,
        "paused": paused,
        "next": list(snapshot.next) if paused else [],
        "values": result if result is not None else snapshot.values,
    }


async def _cli(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the agent graph for a query.")
    parser.add_argument("query", nargs="?", help="User query (State['query']).")
    parser.add_argument("--thread-id", dest="thread_id", default=None)
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume a paused thread (interrupt_before aggregate).",
    )
    args = parser.parse_args(argv)

    if args.resume:
        if not args.thread_id:
            parser.error("--resume requires --thread-id")
        query = args.query or ""
    elif not args.query:
        parser.error("query is required unless --resume")
        return 2
    else:
        query = args.query

    out = await run_query(query, thread_id=args.thread_id, resume=args.resume)
    print(json.dumps(out, default=str, indent=2))
    return 0


def main() -> None:
    raise SystemExit(asyncio.run(_cli()))


if __name__ == "__main__":
    main()
