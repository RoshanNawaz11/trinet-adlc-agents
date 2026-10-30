"""One LangWatch trace per run: every model call of a run — the agents' and the
workers' — shares one W3C traceparent derived from the run session id.
LangWatch traces direct Anthropic calls from the agents."""

from __future__ import annotations

from agents.model import gateway
from agents.queue import pool


async def test_a_worker_runs_inside_its_run(monkeypatch):
    # the worker pool is another process: the run id travels with the sub-task
    monkeypatch.setitem(pool.HANDLERS, "validation.extract", lambda i: gateway.session_id.get())

    seen = await pool.run_subtask({}, {"kind": "validation.extract", "input": {}, "session_id": "run-1"})

    assert seen == "run-1"


def test_traceparent_stable_for_session():
    """Traceparent is stable within a session and differs between sessions."""
    from agents.model.gateway import session_id, traceparent

    # Test context-var path (session_id.set() then traceparent() with no arg)
    session_id.set("session-1")
    trace_1a = traceparent()
    trace_1b = traceparent()
    assert trace_1a == trace_1b, "traceparent should be stable for same session (context-var path)"

    session_id.set("session-2")
    trace_2 = traceparent()
    assert trace_2 != trace_1a, "traceparent should differ between sessions (context-var path)"

    # Test explicit session id path (traceparent(sid) with explicit arg)
    trace_exp_1a = traceparent("session-1")
    trace_exp_1b = traceparent("session-1")
    assert trace_exp_1a == trace_exp_1b, "traceparent should be stable for same session (explicit arg)"

    trace_exp_2 = traceparent("session-2")
    assert trace_exp_2 != trace_exp_1a, "traceparent should differ between sessions (explicit arg)"
