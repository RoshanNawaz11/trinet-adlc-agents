# trinet-agents

A LangGraph multi-agent pipeline that processes WSE termination service orders. A supervisor
Orchestrator routes each order through specialist agents, pauses for a person when an agent
flags an issue, and ends by preparing the final payment package for a person to post.

```
START → orchestrator ─┬─ manual / stop ─────────────────────▶ END
                      ├─▶ validation ──────────┐
                      ├─▶ compliance ──────────┤
                      ├─▶ payroll-calculation ─┤  each returns to the orchestrator
                      ├─▶ review (pause) ──────┘
                      └─▶ execution ─────────────────────────▶ END
```

| Node | What it does |
|---|---|
| `orchestrator` | Supervisor. First visit: looks the order up through MCP and decides the route (`ai` / `manual` / `stop`) and priority. Later visits: updates status, confidence and priority. |
| `validation` | Stage 1: the order is complete and consistent with the employee record. |
| `compliance` | Stage 2: the state's final-pay rules and due date. |
| `payroll-calculation` | Stage 3: final pay, leave payout, deductions; checks against the payroll system. |
| `review` | Pauses once per unresolved flag until a person confirms or declines it. |
| `execution` | Stage 4: prepares the payment package. It never posts or writes anything. |

Each agent's rules live in its Claude Skill under `src/agents/skills/<agent>/skill.md`.

## Quick start

Requires Python 3.11+ and [uv](https://docs.astral.sh/uv/).

```bash
uv sync
cp .env.example .env        # then fill it in (see "Configuration")
uv run run_so.py            # set SO_ID at the top of the file first
```

The agents fetch the service order by id through the MCP server, so the MCP and GraphQL
services must be running.

Other ways to run:

```bash
PYTHONPATH=src uv run python -m agents.runtime.runner SO-1003                      # same, from the CLI
PYTHONPATH=src uv run python -m agents.runtime.runner --thread-id <id> --resume    # continue a paused run
uv run src/agents/runtime/server.py                                                # the HTTP API the backend calls
uv run pytest
```

## How the model is reached

All model calls (chat, MCP tool loop, running Skills, code execution) go through LiteLLM. Skill
uploads are the one exception and go straight to Cloudflare. Both clients live in
`src/agents/model/gateway.py`.

```
model calls:    agents ──▶ LiteLLM :4000 ──(Cloudflare token)──▶ Cloudflare AI Gateway ──(stored Anthropic key)──▶ Anthropic
skill uploads:  agents ──────────────(Cloudflare token)──────▶ Cloudflare AI Gateway ──(stored Anthropic key)──▶ Anthropic
```

- **Model calls** (`require_client()`) need `LITELLM_BASE_URL`. Without it, nodes fall back to
  dummy behaviour (`MissingAPIKeyError`). `ANTHROPIC_API_KEY` is only sent to LiteLLM, so any value
  works (or leave it out) unless LiteLLM has a master key set.
- **Skill uploads** (`require_skills_client()`: list, create, new version) need
  `ANTHROPIC_BASE_URL` + `ANTHROPIC_GATEWAY_TOKEN`. They skip LiteLLM because LiteLLM only proxies
  an older Skills API (different field names) and has no endpoint for uploading a new skill
  version. They are file uploads, not model calls, so nothing useful is lost from tracing.
  Running a skill is a normal model call and still goes through LiteLLM.

Nobody here needs an Anthropic API key. The Anthropic key is stored in the Cloudflare gateway
(BYOK: AI Gateway → `fawm-project-key` → Provider Keys), and Cloudflare adds it to every request
that carries a valid gateway token.

Models per node are set in `src/agents/model/policy.yaml`. The names must match `model_name`
entries in LiteLLM's `litellm_config.yaml`.

## Observability

**Only LiteLLM talks to LangWatch. The agents send nothing.** Set `LANGWATCH_DISABLED=true` in `.env`.

```
agents ──LLM call + x-litellm-session-id: <thread_id>──▶ LiteLLM :4000 ──▶ Cloudflare / Anthropic
                                                            │
                                                            └── OTel (otel callback) ──▶ LangWatch :5560
```

- Every LLM request becomes a trace in LangWatch (model, tokens, latency, and message content).
- MCP tool calls are visible as `tool_use` / `tool_result` blocks inside the LLM messages. They are
  not separate spans, because the agents call the MCP server directly, not through LiteLLM.
- The agents send the run's `thread_id` as `x-litellm-session-id` (see `session_id` in `gateway.py`
  and `run_query` in `runtime/runner.py`) so requests from one run can be grouped.
- **Not captured:** graph or node spans, whole-run traces, non-LLM work. LiteLLM only sees requests
  that pass through it.
- To get the agents' own graph traces instead, leave `LANGWATCH_DISABLED` unset and set
  `LANGWATCH_API_KEY` and `LANGWATCH_ENDPOINT_URL`. That uses the LangWatch SDK from this repo.

Observability never blocks a run. If LangWatch is down or rejects the key, LiteLLM logs the export
error and the request still succeeds.

### The LiteLLM + LangWatch stack

It lives in a separate repo, `llm-gateway-observability-poc/llm-gateway-poc`:

- `docker-compose.yml`: the self-hosted LangWatch stack (UI on http://localhost:5560)
- `litellm_config.yaml`: the LiteLLM proxy config (model entries + the `otel` callback)
- `.env`: LiteLLM's credentials (Cloudflare URL/token or an Anthropic key), the `OTEL_*` variables
  that point at LangWatch, and the LangWatch secrets

Start order (run these in WSL or Git Bash; keep each in its own terminal):

```bash
# 1. LangWatch (Docker Desktop must be running)
docker compose up -d

# 2. LiteLLM. It only reads .env and the config at startup, so restart it after any change.
set -a && source .env && set +a
litellm --config litellm_config.yaml --port 4000

# 3. (optional) the MCP server, then run the agents from this repo
uv run run_so.py
```

The first time, open http://localhost:5560, create a project, and put its API key (Settings → API
Keys) in LiteLLM's `.env` as `LANGWATCH_API_KEY`. `OTEL_HEADERS` reads it from there.

`set -a` exports every variable that `source .env` sets, so the `litellm` process can read them
(`os.environ/...` in the config). Without it they stay in the shell only.

### Connecting LiteLLM to the Cloudflare AI Gateway

Each Claude model gets an entry in `litellm_config.yaml` that points at the gateway:

```yaml
model_list:
  - model_name: claude-haiku-4-5-20251001          # must match policy.yaml
    litellm_params:
      model: anthropic/claude-haiku-4-5-20251001
      api_base: os.environ/ANTHROPIC_BASE_URL      # the gateway's /anthropic URL
      api_key: os.environ/ANTHROPIC_GATEWAY_TOKEN  # LiteLLM requires a key; Cloudflare accepts the token
      extra_headers:
        cf-aig-authorization: os.environ/CF_AIG_AUTH_HEADER   # "Bearer <token>"

litellm_settings:
  callbacks: ["otel"]
```

And in LiteLLM's `.env`:

```
ANTHROPIC_BASE_URL=https://gateway.ai.cloudflare.com/v1/<account-id>/<gateway-id>/anthropic
ANTHROPIC_GATEWAY_TOKEN=<cfut_... token>
CF_AIG_AUTH_HEADER="Bearer ${ANTHROPIC_GATEWAY_TOKEN}"   # must come after ANTHROPIC_GATEWAY_TOKEN
```

When bash sources `.env`, `${VAR}` only sees variables defined on earlier lines, so keep lines that
reference other variables (`CF_AIG_AUTH_HEADER`, `OTEL_HEADERS`) below them. To add another Claude
model, copy the entry, change both model names, add it to `policy.yaml`, and restart LiteLLM.

To check the chain without the agents:

```bash
curl http://localhost:4000/v1/messages -H "x-api-key: anything" -H "anthropic-version: 2023-06-01" \
  -H "content-type: application/json" \
  -d '{"model":"claude-haiku-4-5-20251001","max_tokens":20,"messages":[{"role":"user","content":"hi"}]}'
```

**TLS:** LiteLLM checks Cloudflare's certificate against the public CA list. If a corporate proxy
inspects HTTPS (e.g. Cloudflare WARP) and LiteLLM fails with `CERTIFICATE_VERIFY_FAILED`, set
`SSL_CERT_FILE=/path/to/ca-bundle.pem` in LiteLLM's `.env`. LiteLLM ignores `SSL_CA_BUNDLE`.

## MCP tools (optional)

Set `MCP_SERVER` to enable them. The tool list is discovered from the server at run time, and
the model chooses which to call.

- **Unset:** the agents skip MCP entirely and make plain model calls. Comment the line out. Don't
  set it to an empty value.
- **Set but the server is down:** the run continues without tools after a logged warning
  (the client timeout is 30 s).

Without lookup data the model will often flag or escalate requests that need it.

## Configuration

Copy `.env.example` to `.env`. It is gitignored. Never commit real keys.

| Variable | Needed when | Meaning |
|---|---|---|
| `LITELLM_BASE_URL` | always | `http://localhost:4000` |
| `ANTHROPIC_API_KEY` | LiteLLM has a master key | Sent to LiteLLM only. Optional otherwise. |
| `ANTHROPIC_BASE_URL`, `ANTHROPIC_GATEWAY_TOKEN` | skill uploads | Cloudflare gateway URL (ending in `/anthropic`) and `cfut_...` token |
| `LANGWATCH_DISABLED` | LiteLLM-only observability | `true` |
| `MCP_SERVER` | you want MCP tools | e.g. `http://127.0.0.1:8080/mcp` |
| `LANGWATCH_API_KEY`, `LANGWATCH_ENDPOINT_URL` | only if agents trace themselves | SDK tracing from this repo |

Keep `.env` files that you `source` in WSL with **LF line endings**. CRLF puts a hidden carriage
return at the end of every value and causes `: command not found` errors and failed auth.

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| `400 Invalid model name ...` from LiteLLM | The model in `policy.yaml` isn't in `litellm_config.yaml`, or LiteLLM wasn't restarted after editing it |
| `401 Missing Anthropic API Key` from LiteLLM | LiteLLM's `.env` lacks the Cloudflare variables (or key), or LiteLLM wasn't started with `.env` loaded |
| `ANTHROPIC_BASE_URL / ANTHROPIC_GATEWAY_TOKEN are not set` | This repo's `.env` is missing the two skill-upload variables |
| `401` with `AiGatewayError` / `Unauthorized` | The Cloudflare token is wrong, expired, or not valid for this gateway |
| `ANTHROPIC_API_KEY or ANTHROPIC_AUTH_TOKEN is required for Skills API` | Something called `/v1/skills` on LiteLLM. Skill uploads should use `require_skills_client()` |
| `Failed to export spans ... 401` in the LiteLLM terminal | Wrong or stale `LANGWATCH_API_KEY`, or CRLF line endings in LiteLLM's `.env`. Test the key directly against `http://localhost:5560/api/otel/v1/traces`: 401 means invalid, 400 means accepted |
| Nothing in LangWatch | Look at the project that owns the key and widen the time range. Check the LiteLLM terminal for export errors. |
| `MissingAPIKeyError` / dummy output | No credentials configured for any route |
| Startup validation error about `MCP_SERVER` | It was set to an empty string. Unset it or give it a URL. |

## Layout

```
src/agents/
  graph/          LangGraph definition (build.py), state, routing (edges.py), review pause
  nodes/          orchestrator, validation, compliance, payroll_calculation, execution,
                  and stage_agent.py (the runner the four stage agents share)
  skills/         one skill bundle per agent, Anthropic Skills client, publishing
  model/          gateway.py (the one model client), policy.yaml (model per node)
  tools/          MCP client, tool-use loop (bindings.py), MCP_SERVER setting
  runtime/        runner.py (runs/resumes the graph; CLI), server.py (HTTP API),
                  checkpointer, idempotency
  observability/  optional LangWatch SDK setup (unused when LANGWATCH_DISABLED=true)
tests/            pytest
```
