"""LLM access, isolated behind one interface so no node imports the
Anthropic SDK directly.

This is genuinely live: `complete()` calls the real Anthropic Messages API
via `anthropic.AsyncAnthropic`, using `policy.yaml` to pick model/temperature
per calling node. It only falls back to anything dummy when there's no
`ANTHROPIC_API_KEY` configured at all — that's a deliberate, narrow
exception (see `MissingAPIKeyError` below and how callers use it), not a
general "swallow errors and pretend it worked" fallback. A malformed
response, a bad model name, a rate limit, etc. all raise normally — only
"you haven't configured a key yet" degrades gracefully, so the scaffold
still runs out of the box for anyone who hasn't set one up.
"""

from __future__ import annotations

import os
from pathlib import Path

import anthropic
import yaml

POLICY_PATH = Path(__file__).parent / "policy.yaml"


class MissingAPIKeyError(RuntimeError):
    """Raised by `complete()` when no ANTHROPIC_API_KEY is configured.

    Callers (orchestrator/planner/skills) catch specifically this — never a
    bare `except Exception` — so a real API failure (bad request, rate
    limit, network error) still surfaces loudly instead of silently
    degrading to dummy behavior.
    """


def _load_policy() -> dict:
    return yaml.safe_load(POLICY_PATH.read_text())


class ModelGateway:
    def __init__(self, api_key: str | None = None) -> None:
        self.policy = _load_policy()
        self._api_key = api_key if api_key is not None else os.environ.get("ANTHROPIC_API_KEY")
        self._client = anthropic.AsyncAnthropic(api_key=self._api_key) if self._api_key else None

    @property
    def is_live(self) -> bool:
        return self._client is not None

    def require_client(self) -> anthropic.AsyncAnthropic:
        """Raw client access for callers that need more than `complete()`
        exposes — e.g. `container`/`tools` params for Skills + code
        execution, which have no equivalent in the plain chat-completion
        shape `complete()` wraps. Same missing-key guard as `complete()`,
        so callers get one consistent failure mode either way."""
        if not self.is_live:
            raise MissingAPIKeyError(
                "No ANTHROPIC_API_KEY configured — set it in the environment "
                "to enable real model calls for this node."
            )
        return self._client

    async def complete(self, node: str, system: str, user: str) -> str:
        client = self.require_client()

        config = self.policy.get(node, self.policy["default"])
        # NOTE: temperature is deliberately NOT sent. Anthropic removed
        # temperature/top_p/top_k for current models (Opus 4.7 and later) —
        # a non-default value now gets a 400 from the API, and the anthropic
        # 1.x SDK dropped the parameter from messages.create() entirely, so
        # passing it is a local TypeError before the request even goes out.
        # `temperature` stays in policy.yaml as documentation of the
        # per-node intent (e.g. "orchestrator should be deterministic") for
        # whichever sampling control eventually replaces it — it's read
        # here but not forwarded.
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