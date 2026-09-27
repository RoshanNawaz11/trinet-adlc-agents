"""LLM access, isolated behind one interface so no node imports the
Anthropic SDK directly.

This is genuinely live: `complete()` calls the real Anthropic Messages API
via `anthropic.AsyncAnthropic`, using `policy.yaml` to pick model/temperature
per calling node. Credentials come from `.env` (loaded here via
`python-dotenv`) — either a direct `ANTHROPIC_API_KEY`, or, when
`USE_CLOUDFLARE_AIG=true`, Cloudflare AI Gateway BYOK (`ANTHROPIC_BASE_URL` +
`ANTHROPIC_GATEWAY_TOKEN`), optionally pinned to a custom CA via
`SSL_CA_BUNDLE`. It only falls back to anything dummy when neither is
configured — that's a deliberate, narrow exception (see `MissingAPIKeyError`
below and how callers use it), not a general "swallow errors and pretend it
worked" fallback. A malformed response, a bad model name, a rate limit, etc.
all raise normally — only "you haven't configured credentials yet" degrades
gracefully, so the scaffold still runs out of the box for anyone who hasn't
set one up.
"""

from __future__ import annotations

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
    """Raised by `complete()` when no Anthropic credentials are configured
    (neither a direct ANTHROPIC_API_KEY nor Cloudflare AI Gateway BYOK).

    Callers (orchestrator/planner/skills) catch specifically this — never a
    bare `except Exception` — so a real API failure (bad request, rate
    limit, network error) still surfaces loudly instead of silently
    degrading to dummy behavior.
    """


def _load_policy() -> dict:
    return yaml.safe_load(POLICY_PATH.read_text())


def _ssl_ca_bundle() -> str | None:
    """Path to a custom CA bundle (e.g. a corporate/Cloudflare proxy cert),
    if SSL_CA_BUNDLE is set and actually points at a file on this machine.
    Silently ignored otherwise — .env here is shared across OSes/hosts, so a
    path that only exists on one of them shouldn't break the others."""
    bundle = os.environ.get("SSL_CA_BUNDLE")
    return bundle if bundle and Path(bundle).is_file() else None


# Set by the runtime per run (thread_id). Sent to LiteLLM as its session id so its
# traces can be grouped by run — LiteLLM is the only thing talking to observability.
session_id: ContextVar[str | None] = ContextVar("litellm_session_id", default=None)


async def _add_session_header(request: httpx2.Request) -> None:
    sid = session_id.get()
    if sid:
        request.headers["x-litellm-session-id"] = sid


def _http_client(to_litellm: bool = False) -> httpx2.AsyncClient:
    #httpx2 is used as the anthropic library doesnot accept the httpx library
    kwargs: dict[str, object] = {}
    bundle = _ssl_ca_bundle()
    if bundle:
        kwargs["verify"] = bundle
    if to_litellm:
        kwargs["event_hooks"] = {"request": [_add_session_header]}
    return httpx2.AsyncClient(**kwargs)


def _gateway_token() -> str | None:
    return os.environ.get("ANTHROPIC_GATEWAY_TOKEN") or os.environ.get("CF_AIG_AUTHORIZATION_TOKEN")


def _uses_gateway_byok() -> bool:
    """True when routing through Cloudflare AI Gateway (bring-your-own-key
    at the gateway, not a direct ANTHROPIC_API_KEY) per USE_CLOUDFLARE_AIG."""
    return os.environ.get("USE_CLOUDFLARE_AIG", "").strip().lower() == "true" and bool(_gateway_token())


class ModelGateway:
    def __init__(self, api_key: str | None = None) -> None:
        self.policy = _load_policy()
        self._api_key = api_key if api_key is not None else os.environ.get("ANTHROPIC_API_KEY")
        self._client = self._build_client()

    def _build_client(self) -> anthropic.AsyncAnthropic | None:
        # LiteLLM route: when ANTHROPIC_API_KEY and LITELLM_BASE_URL are both set,
        # every call (chat, tools, skills, code execution) goes through the proxy
        # (e.g. http://localhost:4000/anthropic, its Anthropic pass-through) instead
        # of Cloudflare. Otherwise falls through to the direct/Cloudflare path below.
        litellm_url = os.environ.get("LITELLM_BASE_URL")
        if self._api_key and litellm_url:
            return anthropic.AsyncAnthropic(
                api_key=self._api_key,
                base_url=litellm_url.rstrip("/"),
                http_client=_http_client(to_litellm=True),
            )

        uses_gateway = _uses_gateway_byok()
        if not self._api_key and not uses_gateway:
            return None

        kwargs: dict[str, object] = {"http_client": _http_client()}

        base_url = os.environ.get("ANTHROPIC_BASE_URL")
        if base_url:
            kwargs["base_url"] = base_url.rstrip("/")

        gateway_token = _gateway_token()
        if gateway_token:
            # Cloudflare AI Gateway's own auth header, separate from the
            # Anthropic auth (api_key or auth_token) below.
            kwargs["default_headers"] = {"cf-aig-authorization": f"Bearer {gateway_token}"}

        if uses_gateway:
            return anthropic.AsyncAnthropic(api_key=None, auth_token=gateway_token, **kwargs)
        return anthropic.AsyncAnthropic(api_key=self._api_key, **kwargs)

    def require_client(self) -> anthropic.AsyncAnthropic:
        """Raw client access for callers that need more than `complete()`
        exposes — e.g. `container`/`tools` params for Skills + code
        execution, which have no equivalent in the plain chat-completion
        shape `complete()` wraps. Same missing-credentials guard as
        `complete()`, so callers get one consistent failure mode either way."""
        if self._client is None:
            raise MissingAPIKeyError(
                "No Anthropic credentials configured — set ANTHROPIC_API_KEY, "
                "or USE_CLOUDFLARE_AIG=true with ANTHROPIC_GATEWAY_TOKEN/"
                "ANTHROPIC_BASE_URL, to enable real model calls for this node."
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