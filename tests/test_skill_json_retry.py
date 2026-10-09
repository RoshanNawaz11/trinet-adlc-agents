"""run_skill asks again when the model ends its turn without the JSON answer —
the model is faked, so these run without an API key."""

from __future__ import annotations

from types import SimpleNamespace

from agents.skills.client import JSON_RETRIES, NO_JSON_NUDGE, run_skill

NARRATION = "Good. Now I need the employee record. Let me first ask for it:"
ANSWER = '{"needs": [{"ask": "execution", "request": "Employee record for EMP-1001"}]}'


class FakeMessages:
    def __init__(self, texts: list[str]):
        self.texts = list(texts)
        self.sent: list[str] = []

    async def create(self, **kwargs):
        self.sent.append(kwargs["messages"][0]["content"])
        text = self.texts.pop(0)
        return SimpleNamespace(
            stop_reason="end_turn", usage=None,
            content=[SimpleNamespace(type="text", text=text)],
        )


def _gateway(texts: list[str]) -> tuple[SimpleNamespace, FakeMessages]:
    messages = FakeMessages(texts)
    client = SimpleNamespace(messages=messages)
    return SimpleNamespace(require_client=lambda: client), messages


async def _run(gateway) -> str:
    out = await run_skill("skill", "v1", "{}", model="m", additional_instructions="Return JSON.", gateway=gateway)
    return out["raw_response"]


async def test_a_narrated_answer_is_asked_for_again_with_what_it_said():
    gateway, messages = _gateway([NARRATION, ANSWER])

    assert await _run(gateway) == ANSWER
    assert len(messages.sent) == 2
    assert NARRATION in messages.sent[1]
    assert messages.sent[1].endswith(NO_JSON_NUDGE)


async def test_a_json_answer_is_not_asked_for_again():
    gateway, messages = _gateway([ANSWER])

    assert await _run(gateway) == ANSWER
    assert len(messages.sent) == 1


async def test_it_gives_up_after_the_retries_and_returns_the_last_answer():
    gateway, messages = _gateway([NARRATION] * (JSON_RETRIES + 1))

    assert await _run(gateway) == NARRATION
    assert len(messages.sent) == JSON_RETRIES + 1
