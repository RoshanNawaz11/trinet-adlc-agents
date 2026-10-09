import httpx
import pytest

from agents.runtime.backend import employee_name, events_from_update, lifecycle_event, report_progress


def test_events_from_update_maps_steps_and_open_flags() -> None:
    events = events_from_update(
        {
            "steps": [
                {
                    "stage": "planning",
                    "agent": "Planner",
                    "title": "Planned 3 steps",
                    "source": "Agents",
                    "at": "2026-10-09T10:00:00+00:00",
                }
            ],
            "flags": [
                {
                    "flag_id": "f1",
                    "title": "Net pay mismatch",
                    "resolved": False,
                }
            ],
        },
        employee="Priya Sharma",
    )

    assert events[0]["dedupe_key"] == "step:2026-10-09T10:00:00+00:00:Planned 3 steps"
    assert events[0]["actor"] == "Planner"
    assert events[0]["title"] == "Priya Sharma — Planned 3 steps"
    assert events[1]["dedupe_key"] == "flag:f1"
    assert events[1]["tone"] == "amber"


def test_lifecycle_and_employee_name() -> None:
    assert employee_name({"subjectEmployee": {"fullName": "Jane Doe"}}) == "Jane Doe"
    started = lifecycle_event("started", employee="Jane Doe")
    assert started["dedupe_key"] == "lifecycle:started"
    assert started["action"] == "Started processing"


@pytest.mark.asyncio
async def test_report_progress_posts_to_fastapi(monkeypatch: pytest.MonkeyPatch) -> None:
    posted: dict[str, object] = {}

    class FakeClient:
        def __init__(self, *args: object, **kwargs: object) -> None:
            pass

        async def __aenter__(self) -> "FakeClient":
            return self

        async def __aexit__(self, *args: object) -> None:
            return None

        async def post(self, url: str, json: dict[str, object]) -> httpx.Response:
            posted["url"] = url
            posted["json"] = json
            return httpx.Response(200, json={"id": "run"})

    monkeypatch.setenv("BACKEND_URL", "http://127.0.0.1:8000")
    monkeypatch.setattr("agents.runtime.backend.httpx.AsyncClient", FakeClient)

    await report_progress(
        "11111111-1111-1111-1111-111111111111",
        update={"steps": [{"title": "Check identity", "agent": "Validation Agent", "at": "t1"}]},
        run_status="running",
        employee="Priya Sharma",
    )

    assert posted["url"] == (
        "http://127.0.0.1:8000/api/v1/processing-runs/"
        "11111111-1111-1111-1111-111111111111/events"
    )
    body = posted["json"]
    assert isinstance(body, dict)
    assert body["run_status"] == "running"
    assert body["events"][0]["action"] == "Check identity"
