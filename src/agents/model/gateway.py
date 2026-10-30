"""
Model gateway providing direct access to the Anthropic API.

This module creates a single Anthropic client instance used for both
model calls and skill uploads. Tracing is handled by LangWatch.
"""

from __future__ import annotations

import hashlib
import os
from contextvars import ContextVar
from pathlib import Path

import anthropic
import yaml
from dotenv import load_dotenv

load_dotenv()

POLICY_PATH = Path(__file__).parent / "policy.yaml"


class MissingAPIKeyError(RuntimeError):
    """Raised when `ANTHROPIC_API_KEY` is not set.

    Callers catch specifically this — never a bare `except Exception` — so a
    real API failure (bad request, rate limit, network error) still surfaces
    loudly instead of silently degrading.
    """


def _load_policy() -> dict:
    return yaml.safe_load(POLICY_PATH.read_text())


# Set by the runtime per run (thread_id), and by the worker pool per sub-task.
# LangWatch traces the run from this session id. traceparent() is a W3C trace
# context derived from it, so every call of one run — agents and workers —
# lands in one trace. trace_id() is the id returned on run results.
session_id: ContextVar[str | None] = ContextVar("run_session_id", default=None)


def traceparent(sid: str | None = None) -> str:
    """The same trace id and root span id for every call of a run.

    Pass a session id, or omit it to use the current `session_id` context.
    """
    if sid is None:
        sid = session_id.get()
    if not sid:
        raise ValueError("session id is not set")
    h = hashlib.sha256(sid.encode()).hexdigest()
    return f"00-{h[:32]}-{h[32:48]}-01"


def trace_id(sid: str) -> str:
    """The run's trace id in LangWatch."""
    return traceparent(sid).split("-")[1]


class ModelGateway:
    def __init__(self) -> None:
        self.policy = _load_policy()
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise MissingAPIKeyError("ANTHROPIC_API_KEY is not set")

        kwargs: dict[str, str] = {"api_key": api_key}
        base_url = os.getenv("ANTHROPIC_BASE_URL")
        if base_url:
            kwargs["base_url"] = base_url

        self._client = anthropic.AsyncAnthropic(**kwargs)

    def require_client(self) -> anthropic.AsyncAnthropic:
        """Raw client access for callers that need more than `complete()`."""
        return self._client

    def require_skills_client(self) -> anthropic.AsyncAnthropic:
        """Same client as `require_client()`; skill uploads use the Anthropic API directly."""
        return self._client

    async def complete(self, node: str, system: str, user: str) -> str:
        client = self.require_client()

        config = self.policy.get(node, self.policy["default"])
        # NOTE: temperature is deliberately NOT sent. Anthropic removed
        # temperature/top_p/top_k for current models (Opus 4.7 and later) —
        response = await client.messages.create(
            model=config["model"],
            max_tokens=config.get("max_tokens", 1024),
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return "".join(block.text for block in response.content if block.type == "text")


_default_gateway: ModelGateway | None = None


def get_default_gateway() -> ModelGateway:
    """Process-wide singleton, so every node shares one client (and one
    read of policy.yaml) instead of constructing its own. Nodes/skills can
    still pass their own `ModelGateway` instance explicitly — e.g. in tests,
    to inject a fake — since every real/skill function takes `gateway` as an
    optional parameter rather than importing this function directly.
    """
    global _default_gateway
    if _default_gateway is None:
        _default_gateway = ModelGateway()
    return _default_gateway
