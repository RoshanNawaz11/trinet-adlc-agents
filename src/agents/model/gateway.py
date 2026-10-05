"""LLM access, isolated behind one interface so no node imports the
Anthropic SDK directly.

Every model call goes through LiteLLM:

    agents ──▶ LiteLLM (LITELLM_BASE_URL) ──▶ Cloudflare AI Gateway ──▶ Anthropic

Skill uploads are the one exception and go straight to Cloudflare
(ANTHROPIC_BASE_URL + ANTHROPIC_GATEWAY_TOKEN), see `require_skills_client()`.
Cloudflare holds the Anthropic key, so this repo needs no real one.
`ANTHROPIC_API_KEY` is only sent to LiteLLM (any value works unless LiteLLM
has a master key set). `policy.yaml` picks the model per calling node.

Only "LITELLM_BASE_URL isn't set" degrades gracefully (see
`MissingAPIKeyError`); a bad request, rate limit, etc. all raise normally.
"""

from __future__ import annotations

import hashlib
import os
from contextvars import ContextVar
from pathlib import Path

import anthropic
import httpx2
import yaml
from dotenv import load_dotenv

load_dotenv()

POLICY_PATH = Path(__file__).parent / "policy.yaml"


class MissingAPIKeyError(RuntimeError):
    """Raised by `complete()` when LITELLM_BASE_URL isn't configured.

    Callers (orchestrator/planner/skills) catch specifically this — never a
    bare `except Exception` — so a real API failure (bad request, rate
    limit, network error) still surfaces loudly instead of silently
    degrading to dummy behavior.
    """


def _load_policy() -> dict:
    return yaml.safe_load(POLICY_PATH.read_text())


# Set by the runtime per run (thread_id), and by the worker pool per sub-task.
# Sent to LiteLLM as its session id, and as a W3C traceparent: LiteLLM's otel
# callback starts its spans from it, so every call of one run — agents and
# workers — lands in one LangWatch trace, with the run's total cost.
session_id: ContextVar[str | None] = ContextVar("litellm_session_id", default=None)


def traceparent(sid: str) -> str:
    """The same trace id and root span id for every call of a run."""
    h = hashlib.sha256(sid.encode()).hexdigest()
    return f"00-{h[:32]}-{h[32:48]}-01"


async def _add_session_header(request: httpx2.Request) -> None:
    sid = session_id.get()
    if sid:
        request.headers["x-litellm-session-id"] = sid
        request.headers["traceparent"] = traceparent(sid)


class ModelGateway:
    def __init__(self, api_key: str | None = None) -> None:
        self.policy = _load_policy()
        self._client = self._build_client(api_key or os.environ.get("ANTHROPIC_API_KEY") or "litellm")
        self._skills_client = self._build_skills_client()

    @staticmethod
    def _build_skills_client() -> anthropic.AsyncAnthropic | None:
        # Skill uploads (list/create/new version) go straight to Cloudflare:
        # LiteLLM only proxies an older Skills API and has no versions endpoint.
        base_url = os.environ.get("ANTHROPIC_BASE_URL")
        token = os.environ.get("ANTHROPIC_GATEWAY_TOKEN")
        if not (base_url and token):
            return None
        return anthropic.AsyncAnthropic(
            api_key=token,
            base_url=base_url.rstrip("/"),
            default_headers={"cf-aig-authorization": f"Bearer {token}"},
            http_client=httpx2.AsyncClient(),
        )

    def _build_client(self, api_key: str) -> anthropic.AsyncAnthropic | None:
        base_url = os.environ.get("LITELLM_BASE_URL")
        if not base_url:
            return None
        #httpx2 is used as the anthropic library doesnot accept the httpx library
        return anthropic.AsyncAnthropic(
            api_key=api_key,
            base_url=base_url.rstrip("/"),
            http_client=httpx2.AsyncClient(event_hooks={"request": [_add_session_header]}),
        )

    def require_client(self) -> anthropic.AsyncAnthropic:
        """Raw client access for callers that need more than `complete()`
        exposes — e.g. `container`/`tools` params for Skills + code
        execution, which have no equivalent in the plain chat-completion
        shape `complete()` wraps. Same missing-config guard as
        `complete()`, so callers get one consistent failure mode either way."""
        if self._client is None:
            raise MissingAPIKeyError(
                "LITELLM_BASE_URL is not set — point it at the LiteLLM proxy "
                "(e.g. http://localhost:4000) to enable real model calls for this node."
            )
        return self._client

    def require_skills_client(self) -> anthropic.AsyncAnthropic:
        """Client for the Skills upload API only. Running a skill still uses
        `require_client()`, so it goes through LiteLLM and gets traced."""
        if self._skills_client is None:
            raise MissingAPIKeyError(
                "ANTHROPIC_BASE_URL / ANTHROPIC_GATEWAY_TOKEN are not set — "
                "skill uploads go straight to the Cloudflare AI Gateway."
            )
        return self._skills_client

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
