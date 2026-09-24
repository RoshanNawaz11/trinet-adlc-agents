"""Process entrypoint: build the compiled graph and invoke/resume it.

This is the runtime worker (queue consumer / CLI), not nodes/worker
(the classify skill node).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
import uuid
from pathlib import Path
from typing import Any

import langwatch
from langwatch.telemetry.tracing import trace
from langwatch.telemetry.context import get_current_trace
_SRC_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if _SRC_ROOT not in sys.path:
    sys.path.insert(0, _SRC_ROOT)

from agents.graph.build import build_graph
from agents.runtime.idempotency import already_processed, idempotency_key, mark_processed
from agents.runtime.samples import SAMPLES, format_samples, resolve_query
from agents.observability.langwatch_setup import langwatch_setup
from agents.observability.tracing import attach_metadata, maybe_trace

_graph = None
_LOG_DIR = Path(__file__).resolve().parent.parent.parent.parent / "logs"


def _setup_logging() -> None:

    _LOG_DIR.mkdir(parents=True, exist_ok=True)
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    fmt = logging.Formatter("%(asctime)s %(levelname)-7s %(name)s: %(message)s")

    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(fmt)
    root.addHandler(console)

    file_handler = logging.FileHandler(_LOG_DIR / "agents.log", encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(fmt)
    root.addHandler(file_handler)


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
    return {
        "configurable": {"thread_id": thread_id},
        "callbacks": [get_current_trace().get_langchain_callback()],
        }

@maybe_trace("run-agent-query")
async def run_query(
    query: str,
    *,
    thread_id: str | None = None,
    resume: bool = False,
) -> dict[str, Any]:
    graph = get_graph()
    thread_id = thread_id or str(uuid.uuid4())
    attach_metadata(thread_id=thread_id, resume=resume)
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
        # Guard against restarting a thread that's mid-run instead of
        # resuming it. A queue redelivery calling this without --resume
        # on a paused thread_id would otherwise silently re-invoke with
        # a fresh initial_state on top of existing checkpoint history —
        # and Worker's dispatch step calls non-idempotent live actions
        # (notify_on_call, create_ticket), so a silent restart risks
        # firing those twice.
        snapshot = await graph.aget_state(config)
        if snapshot.next:
            raise RuntimeError(
                f"Thread {thread_id} is paused mid-run (next={list(snapshot.next)}) — "
                "use --resume, not a fresh query, or you will restart instead of continue."
            )
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
    parser.add_argument(
        "--sample",
        dest="sample",
        default=None,
        metavar="NAME",
        help=f"Named sample query instead of typing one. Known: {', '.join(sorted(SAMPLES))}.",
    )
    parser.add_argument(
        "--list-samples",
        action="store_true",
        help="Print named sample queries and exit.",
    )
    parser.add_argument("--thread-id", dest="thread_id", default=None)
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume a paused thread (interrupt_before aggregate).",
    )
    args = parser.parse_args(argv)

    if args.list_samples:
        print(format_samples())
        return 0

    if args.resume and not args.thread_id:
        parser.error("--resume requires --thread-id")

    try:
        query = resolve_query(query=args.query, sample=args.sample, resume=args.resume)
    except (KeyError, ValueError) as exc:
        parser.error(str(exc))

    out = await run_query(query, thread_id=args.thread_id, resume=args.resume)
    print(json.dumps(out, default=str, indent=2))
    return 0


def main() -> None:
    _setup_logging()
    langwatch_setup()
    raise SystemExit(asyncio.run(_cli()))


if __name__ == "__main__":
    main()