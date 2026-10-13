"""The service-order worker records run status for FastAPI to poll."""

import asyncio
import json

import pytest

from agents.queue import orders


class FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}
        self.history: list[dict[str, str]] = []

    async def set(self, key: str, value: str, ex: int | None = None) -> None:
        self.values[key] = value
        self.history.append(json.loads(value))


@pytest.mark.asyncio
async def test_start_records_running_then_paused(monkeypatch: pytest.MonkeyPatch) -> None:
    redis = FakeRedis()

    async def fake_run_query(*args, **kwargs):
        assert args[0] == "describe SO-1003"
        assert kwargs["resume"] is False
        assert kwargs["thread_id"] == "run-1"
        return {"thread_id": "run-1", "paused": True, "values": {"status": "running"}}

    monkeypatch.setattr(orders, "run_query", fake_run_query)

    result = await orders.process_service_order(
        {"redis": redis}, {"thread_id": "run-1", "query": "describe SO-1003"}
    )

    assert result["status"] == "paused"
    assert [item["status"] for item in redis.history] == ["running", "paused"]


@pytest.mark.asyncio
async def test_resume_records_done(monkeypatch: pytest.MonkeyPatch) -> None:
    redis = FakeRedis()

    async def fake_run_query(*args, **kwargs):
        assert kwargs["resume"] is True
        assert kwargs["decision"] == {"action": "approve"}
        return {"thread_id": "run-1", "paused": False, "values": {"status": "done"}}

    monkeypatch.setattr(orders, "run_query", fake_run_query)

    result = await orders.resume_service_order(
        {"redis": redis},
        {"thread_id": "run-1", "decision": {"action": "approve"}},
    )

    assert result["status"] == "done"
    assert json.loads(redis.values["order-run:run-1"]) == {"status": "done"}


@pytest.mark.asyncio
async def test_a_failed_run_is_recorded_and_not_raised(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    redis = FakeRedis()

    async def fake_run_query(*args, **kwargs):
        raise RuntimeError("orchestrator blew up")

    monkeypatch.setattr(orders, "run_query", fake_run_query)

    result = await orders.process_service_order(
        {"redis": redis}, {"thread_id": "run-1", "query": "q"}
    )

    assert result["status"] == "failed"
    assert "orchestrator blew up" in result["error"]
    assert json.loads(redis.values["order-run:run-1"]) == {
        "status": "failed",
        "error": "orchestrator blew up",
    }


@pytest.mark.asyncio
async def test_a_cancelled_run_is_recorded_as_failed_and_still_cancels(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """arq cancels the job task at job_timeout or on shutdown."""
    redis = FakeRedis()
    started = asyncio.Event()

    async def fake_run_query(*args, **kwargs):
        started.set()
        await asyncio.sleep(3600)

    monkeypatch.setattr(orders, "run_query", fake_run_query)

    task = asyncio.create_task(
        orders.process_service_order({"redis": redis}, {"thread_id": "run-1", "query": "q"})
    )
    await started.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    status = json.loads(redis.values["order-run:run-1"])
    assert status["status"] == "failed"
    assert "job limit" in status["error"]
    assert [item["status"] for item in redis.history] == ["running", "failed"]


@pytest.mark.asyncio
async def test_a_run_that_outlasts_the_job_timeout_is_recorded_as_failed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The way arq enforces job_timeout: asyncio.wait_for around the job."""
    redis = FakeRedis()

    async def fake_run_query(*args, **kwargs):
        await asyncio.sleep(3600)

    monkeypatch.setattr(orders, "run_query", fake_run_query)

    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(
            orders.process_service_order({"redis": redis}, {"thread_id": "run-1", "query": "q"}),
            timeout=0.05,
        )

    assert json.loads(redis.values["order-run:run-1"])["status"] == "failed"
