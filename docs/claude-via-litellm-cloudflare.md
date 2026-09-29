# Claude via LiteLLM → Cloudflare AI Gateway → Anthropic

How trinet_agents reaches Claude, and how to set up the same thing for another agent project
(e.g. ADLC). Everything below is copied from a working setup; placeholders are in `<angle brackets>`.

## 1. The flow

```
model calls:    agents ──HTTP──▶ LiteLLM :4000 ──HTTPS + CF token──▶ Cloudflare AI Gateway ──stored Anthropic key──▶ Anthropic
skill uploads:  agents ──────────────HTTPS + CF token──────────────▶ Cloudflare AI Gateway ──stored Anthropic key──▶ Anthropic
traces:                          LiteLLM ──OpenTelemetry──▶ LangWatch :5560
```

| Piece | Job |
|---|---|
| **Agents** | Use the normal Anthropic Python SDK, pointed at LiteLLM. Hold no Anthropic key. |
| **LiteLLM proxy** | The only thing that makes model calls. Maps the model name to the Cloudflare gateway and traces every call to LangWatch. |
| **Cloudflare AI Gateway** | Checks the gateway token, adds the Anthropic key it stores (BYOK), forwards to Anthropic. Also logs every request. |
| **LangWatch** | Self-hosted trace UI (Docker Compose). |

Why this shape:
- **No Anthropic key on any laptop or server.** It lives only in Cloudflare. Revoking someone means
  disabling their Cloudflare token.
- **One place for tracing.** The agents send nothing to LangWatch; LiteLLM traces every call.
- **Swappable.** The agents only know "an Anthropic-compatible URL". Moving LiteLLM or Cloudflare
  doesn't touch agent code.

**Skill uploads are the one exception.** LiteLLM's `/v1/skills` proxy uses an older Skills API
(different field names) and has no endpoint for new skill versions, so uploads go straight to
Cloudflare. *Running* a skill is a normal `/v1/messages` call and does go through LiteLLM. If a
project doesn't use Anthropic Skills, it only needs the first route.

## 2. Credentials: who holds what

| Credential | Where it lives | Notes |
|---|---|---|
| Anthropic API key | Cloudflare dashboard → AI → AI Gateway → `<gateway>` → Provider Keys | Nobody else needs it |
| Cloudflare gateway token (`cfut_...`) | LiteLLM `.env`; agents `.env` only for skill uploads | One per person/service, so each can be revoked |
| LangWatch project key | LiteLLM `.env` | Created in your own LangWatch UI |
| LangWatch secrets, ClickHouse password | LiteLLM `.env` (read by `docker-compose.yml`) | Generate with `openssl rand -hex 32` |

Never commit `.env` files or send them in chat. Share tokens through a password manager.

## 3. Setup

### 3.1 Cloudflare AI Gateway (once per project)

1. Cloudflare dashboard → AI → AI Gateway → **Create gateway** (e.g. `adlc`). Turn on
   **Authenticated Gateway**.
2. Gateway → **Provider Keys** → add the Anthropic API key.
3. Create a gateway token (`cfut_...`).
4. The Anthropic endpoint is:
   ```
   https://gateway.ai.cloudflare.com/v1/<account-id>/<gateway-id>/anthropic
   ```
   Use this one. `https://api.cloudflare.com/client/v4/accounts/<id>/ai/run` is **Workers AI**
   (Cloudflare-hosted models), a different product that does not reach Anthropic.

Check it with only the token, no Anthropic key:

```bash
curl https://gateway.ai.cloudflare.com/v1/<account-id>/<gateway-id>/anthropic/v1/messages \
  -H "cf-aig-authorization: Bearer <cf token>" \
  -H "anthropic-version: 2023-06-01" -H "content-type: application/json" \
  -d '{"model":"claude-haiku-4-5-20251001","max_tokens":20,"messages":[{"role":"user","content":"hi"}]}'
```

A reply from Claude means the gateway has a stored key. `401 ... API key` means it doesn't.

### 3.2 LiteLLM + LangWatch

Reuse the gateway repo as is:
`git.z-apps.io:maneesh.bachu/llm-gateway-observability-poc.git`, branch `servers-only`, folder
`llm-gateway-poc/`. Its README has full details. The only project-specific part is the model list.

**`litellm_config.yaml`**: one entry per Claude model. `model_name` is what the agents ask for.

```yaml
model_list:
  - model_name: claude-haiku-4-5-20251001
    litellm_params:
      model: anthropic/claude-haiku-4-5-20251001
      api_base: os.environ/ANTHROPIC_BASE_URL
      api_key: os.environ/ANTHROPIC_GATEWAY_TOKEN   # LiteLLM requires a key; Cloudflare accepts the token
      extra_headers:
        cf-aig-authorization: os.environ/CF_AIG_AUTH_HEADER

litellm_settings:
  callbacks: ["otel"]
```

**`.env`**: a `${VAR}` only sees variables defined *above* it, so keep this order:

```
ANTHROPIC_BASE_URL=https://gateway.ai.cloudflare.com/v1/<account-id>/<gateway-id>/anthropic
ANTHROPIC_GATEWAY_TOKEN=<cf token>
CF_AIG_AUTH_HEADER="Bearer ${ANTHROPIC_GATEWAY_TOKEN}"

LANGWATCH_API_KEY=<langwatch project key>
OTEL_EXPORTER=otlp_http
OTEL_ENDPOINT=http://localhost:5560/api/otel/v1/traces
OTEL_HEADERS="Authorization=Bearer ${LANGWATCH_API_KEY}"
OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT=span_only

NEXTAUTH_SECRET=<openssl rand -hex 32>
API_TOKEN_JWT_SECRET=<openssl rand -hex 32>
CREDENTIALS_SECRET=<openssl rand -hex 32>
CLICKHOUSE_PASSWORD=langwatch
```

**Start** (WSL or Git Bash, each in its own terminal):

```bash
cd llm-gateway-poc
docker compose --env-file .env up -d          # LangWatch; first time: create a project at
                                              # http://localhost:5560 and put its key in .env

source llm-gateway-venv/bin/activate          # new machine: python3 -m venv llm-gateway-venv &&
                                              #   pip install 'litellm[proxy]' opentelemetry-sdk opentelemetry-exporter-otlp-proto-http
set -a && source .env && set +a               # export every .env variable to litellm
litellm --config litellm_config.yaml --port 4000
```

LiteLLM reads `.env` and the config only at startup; restart it after any change.

### 3.3 The agent project

**`.env`**:

```
LITELLM_BASE_URL=http://localhost:4000
LANGWATCH_DISABLED=true                  # LiteLLM does the tracing
# only if the project uses Anthropic Skills:
ANTHROPIC_BASE_URL=https://gateway.ai.cloudflare.com/v1/<account-id>/<gateway-id>/anthropic
ANTHROPIC_GATEWAY_TOKEN=<cf token>
```

**Code**: put all Claude access behind one module, so nothing else imports the SDK with its own
settings. Minimal version (trinet_agents' is `src/agents/model/gateway.py`):

```python
import os
from contextvars import ContextVar

import anthropic
import httpx  # trinet_agents uses httpx2 because of its anthropic SDK version; plain httpx is fine otherwise

# set once per run (e.g. the run/thread id); LiteLLM groups traces by it
session_id: ContextVar[str | None] = ContextVar("litellm_session_id", default=None)

async def _add_session_header(request: httpx.Request) -> None:
    if sid := session_id.get():
        request.headers["x-litellm-session-id"] = sid

def model_client() -> anthropic.AsyncAnthropic:
    """Every model call: agents → LiteLLM → Cloudflare → Anthropic."""
    return anthropic.AsyncAnthropic(
        api_key=os.environ.get("ANTHROPIC_API_KEY") or "litellm",   # LiteLLM has no auth unless you add a master key
        base_url=os.environ["LITELLM_BASE_URL"].rstrip("/"),
        http_client=httpx.AsyncClient(event_hooks={"request": [_add_session_header]}),
    )

def skills_client() -> anthropic.AsyncAnthropic:
    """Skill uploads only (skills.list / create / versions.create): straight to Cloudflare."""
    token = os.environ["ANTHROPIC_GATEWAY_TOKEN"]
    return anthropic.AsyncAnthropic(
        api_key=token,
        base_url=os.environ["ANTHROPIC_BASE_URL"].rstrip("/"),
        default_headers={"cf-aig-authorization": f"Bearer {token}"},
    )
```

At the start of each run: `session_id.set(<run id>)`. Then call Claude as usual:

```python
client = model_client()
resp = await client.messages.create(model="claude-haiku-4-5-20251001", max_tokens=4096, messages=[...])
```

The `model` must be a `model_name` in `litellm_config.yaml`.

### 3.4 Anthropic Skills (optional)

trinet_agents keeps each agent's instructions as a skill bundle (`src/agents/skills/<agent>/skill.md`)
and runs it in Anthropic's code-execution sandbox. The files to reuse:

| File in trinet_agents | What it does | Change for ADLC |
|---|---|---|
| `src/agents/skills/loader.py` | Reads a bundle folder; renames `skill.md` → `SKILL.md` and adds the required `name`/`description` frontmatter | Nothing |
| `src/agents/skills/registry.py` | Uploads a bundle only when its files changed (content hash); caches ids in `.cache/registry.json` | Nothing (see limits below) |
| `src/agents/skills/client.py` | `publish_bundle` / `publish_bundle_version` / `find_remote_skill_by_name` via `skills_client()`; `run_skill` via `model_client()` | Import path of the gateway |
| `src/agents/tools/bindings.py` | Skill + MCP tools in one loop (model asks for a tool → run it locally → send result back) | Only if ADLC uses MCP |

Running a skill:

```python
resp = await model_client().messages.create(
    model="claude-haiku-4-5-20251001",
    max_tokens=4096,                        # 1024 cuts off answers once the sandbox is used
    container={"skills": [{"type": "custom", "skill_id": skill_id, "version": version_id}]},
    tools=[{"type": "code_execution_20250825", "name": "code_execution"}],
    messages=[{"role": "user", "content": "..."}],
)
```

Limits to know before copying:
- **Sandbox outages**: Anthropic sometimes returns `503 overloaded_error: Code execution container
  setup is temporarily unavailable`. The run fails. If a skill is only markdown (no scripts), sending
  its text as the system prompt instead avoids the sandbox and uses far fewer input tokens
  (a skill run through the sandbox was ~10,500 input tokens).
- **The id cache is a local file.** It's lost on redeploy and not shared between instances. For
  production, publish skills from CI and look them up by name at runtime.
- **The Anthropic account behind the gateway is shared.** Skill names should be unique to the
  project (e.g. prefix with `ADLC `).

## 4. Check each hop

| Hop | How |
|---|---|
| Cloudflare → Anthropic | The `curl` in 3.1 |
| LiteLLM → Cloudflare → Anthropic | `curl http://localhost:4000/v1/messages -H "x-api-key: x" -H "anthropic-version: 2023-06-01" -H "content-type: application/json" -d '{"model":"claude-haiku-4-5-20251001","max_tokens":20,"messages":[{"role":"user","content":"hi"}]}'` |
| Traces | The request shows up in LangWatch (`localhost:5560`) and in Cloudflare → AI Gateway → Logs |
| Agents | Run one job; the agent log shows `POST http://localhost:4000/v1/messages 200` |

## 5. Troubleshooting

| Symptom | Cause |
|---|---|
| `400 Invalid model name` | The model isn't a `model_name` in `litellm_config.yaml`, or LiteLLM wasn't restarted |
| `401 Missing Anthropic API Key` from LiteLLM | `.env` not loaded: start with `set -a && source .env && set +a` |
| `401 AiGatewayError / Unauthorized` | Cloudflare token wrong, expired, or not for this gateway |
| `ANTHROPIC_API_KEY or ANTHROPIC_AUTH_TOKEN is required for Skills API` | A skill upload went to LiteLLM; use `skills_client()` |
| `Unexpected Skills API response — missing IDs` | Same: LiteLLM returned the old Skills format |
| `503 overloaded_error ... Code execution container` | Anthropic sandbox capacity; retry later (see 3.4) |
| `Failed to export spans ... 401` in LiteLLM | Wrong `LANGWATCH_API_KEY`, or `OTEL_HEADERS` is above `LANGWATCH_API_KEY` in `.env` |
| `CERTIFICATE_VERIFY_FAILED` | Corporate TLS inspection: set `SSL_CERT_FILE=<full CA bundle>` in LiteLLM's `.env` (LiteLLM ignores `SSL_CA_BUNDLE`) |
| `: command not found` when sourcing `.env` | CRLF line endings; save as LF |

## 6. Reference

| What | Where |
|---|---|
| Agents repo | `git.z-apps.io:roshan.syed/trinet_poc.git`, branch `agents-ui` |
| Gateway + LangWatch repo | `git.z-apps.io:maneesh.bachu/llm-gateway-observability-poc.git`, branch `servers-only` |
| Gateway client | `src/agents/model/gateway.py` |
| Model per agent | `src/agents/model/policy.yaml` |
| Skills | `src/agents/skills/` |
| Env templates | `.env.example` in both repos |
