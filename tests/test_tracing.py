"""One LangWatch trace per run: every model call of a run — the agents' and the
workers' — carries the same W3C traceparent, which LiteLLM's otel callback
starts its spans from."""

from __future__ import annotations

import re

import httpx2

from agents.model import gateway
from agents.queue import pool


async def test_every_call_of_a_run_carries_the_same_traceparent():
    token = gateway.session_id.set("run-1")
    try:
        first, second = httpx2.Request("POST", "http://litellm/v1/messages"), httpx2.Request("POST", "http://litellm/v1/messages")
        await gateway._add_session_header(first)
        await gateway._add_session_header(second)
    finally:
        gateway.session_id.reset(token)

    assert first.headers["x-litellm-session-id"] == "run-1"
    assert re.fullmatch(r"00-[0-9a-f]{32}-[0-9a-f]{16}-01", first.headers["traceparent"])
    assert first.headers["traceparent"] == second.headers["traceparent"]
    assert gateway.traceparent("run-2") != first.headers["traceparent"]


async def test_no_run_no_headers():
    request = httpx2.Request("POST", "http://litellm/v1/messages")
    await gateway._add_session_header(request)
    assert "traceparent" not in request.headers


async def test_a_worker_runs_inside_its_run(monkeypatch):
    # the worker pool is another process: the run id travels with the sub-task
    monkeypatch.setitem(pool.HANDLERS, "validation.extract", lambda i: gateway.session_id.get())

    seen = await pool.run_subtask({}, {"kind": "validation.extract", "input": {}, "session_id": "run-1"})

    assert seen == "run-1"
