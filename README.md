# trinet-agents

A LangGraph multi-agent pipeline that takes a free-text request, looks up data through MCP tools,
plans the work, and runs two Claude Skills (summarize, classify). It ends in a status of `done`
or `needs_review`, and pauses for a human before the final `aggregate` step.

```
query → orchestrator → planner → expert (summarize) → classify_gate → worker (classify) → aggregate → END
            │                          │                                     │
      MCP tool calls             Claude Skill                          Claude Skill
      (optional)             (code-execution sandbox)              (code-execution sandbox)
```

| Node | What it does |
|---|---|
| `orchestrator` | First model call. Can call MCP tools (e.g. look up an employee) and decides whether to flag the request. |
| `planner` | Turns the query and any MCP results into steps (`summarize`, `classify`). |
| `expert` | Runs the `summarize` skill. |
| `worker` | Runs the `classify` skill on the expert's output. |
| `aggregate` | Collects results. Status is `done`, `needs_review` (any escalation) or `failed`. The graph **pauses before** this node so a person can review. |

## Quick start

Requires Python 3.11+ and [uv](https://docs.astral.sh/uv/).

```bash
uv sync
cp .env.example .env        # then fill it in (see "Configuration")
uv run run_query.py         # edit QUERY at the top of the file first
```

Other ways to run:

```bash
PYTHONPATH=src uv run python -m agents.runtime.worker --list-samples
PYTHONPATH=src uv run python -m agents.runtime.worker --sample checkout
PYTHONPATH=src uv run python -m agents.runtime.worker --thread-id <id> --resume    # continue a paused run
uv run pytest
```

(`main.py` is a placeholder. Use `run_query.py` or the worker CLI.)

## How the model is reached

All model calls (chat, MCP tool loop, Skills, code execution) go through one client in
`src/agents/model/gateway.py`. Which route it uses depends on `.env`:

| Route | Turned on by | Path |
|---|---|---|
| **LiteLLM** (recommended) | `ANTHROPIC_API_KEY` **and** `LITELLM_BASE_URL` both set | agents → LiteLLM → (Cloudflare AI Gateway or Anthropic) |
| **Cloudflare direct** | `USE_CLOUDFLARE_AIG=true` + `ANTHROPIC_GATEWAY_TOKEN` + `ANTHROPIC_BASE_URL` | agents → Cloudflare AI Gateway → Anthropic |
| **Direct Anthropic** | only a real `ANTHROPIC_API_KEY` | agents → Anthropic |
| none | no credentials | nodes fall back to dummy behaviour (`MissingAPIKeyError`) |

With the LiteLLM route on, `ANTHROPIC_API_KEY` in this repo only acts as the switch. Any non-empty
value works, and the real credentials live in LiteLLM's own `.env`.

Models per node are set in `src/agents/model/policy.yaml`. The names must match model names
configured in LiteLLM.

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
  and `run_query` in `runtime/worker.py`) so requests from one run can be grouped.
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
uv run run_query.py
```

The first time, open http://localhost:5560, create a project, and put its API key (Settings → API
Keys) in LiteLLM's `.env` as `LANGWATCH_API_KEY`. `OTEL_HEADERS` reads it from there.

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
| `ANTHROPIC_API_KEY` | LiteLLM route (any value) or direct Anthropic (real key) | Switches routes, see above |
| `LITELLM_BASE_URL` | LiteLLM route | `http://localhost:4000` |
| `LANGWATCH_DISABLED` | LiteLLM-only observability | `true` |
| `USE_CLOUDFLARE_AIG`, `ANTHROPIC_GATEWAY_TOKEN`, `ANTHROPIC_BASE_URL` | Cloudflare direct | Cloudflare AI Gateway BYOK |
| `SSL_CA_BUNDLE` | corporate or Cloudflare CA | Path to a CA bundle. Ignored if the file doesn't exist. |
| `MCP_SERVER` | you want MCP tools | e.g. `http://127.0.0.1:8080/mcp` |
| `LANGWATCH_API_KEY`, `LANGWATCH_ENDPOINT_URL` | only if agents trace themselves | SDK tracing from this repo |

Keep `.env` files that you `source` in WSL with **LF line endings**. CRLF puts a hidden carriage
return at the end of every value and causes `: command not found` errors and failed auth.

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| `400 Invalid model name ...` from LiteLLM | The model in `policy.yaml` isn't in `litellm_config.yaml`, or LiteLLM wasn't restarted after editing it |
| `401 Missing Anthropic API Key` from LiteLLM | LiteLLM's `.env` lacks the Cloudflare variables (or key), or LiteLLM wasn't started with `.env` loaded |
| `Failed to export spans ... 401` in the LiteLLM terminal | Wrong or stale `LANGWATCH_API_KEY`, or CRLF line endings in LiteLLM's `.env`. Test the key directly against `http://localhost:5560/api/otel/v1/traces`: 401 means invalid, 400 means accepted |
| Nothing in LangWatch | Look at the project that owns the key and widen the time range. Check the LiteLLM terminal for export errors. |
| `MissingAPIKeyError` / dummy output | No credentials configured for any route |
| Startup validation error about `MCP_SERVER` | It was set to an empty string. Unset it or give it a URL. |

## Layout

```
src/agents/
  graph/          LangGraph definition (build.py), state, routing, interrupt points
  nodes/          orchestrator, planner, expert, worker
  skills/         skill bundles (classify, summarize), Anthropic Skills client, publishing
  model/          gateway.py (the one model client), policy.yaml (model per node)
  tools/          MCP client, tool-use loop (bindings.py), MCP_SERVER setting
  runtime/        worker CLI/entrypoint, checkpointer, idempotency, sample queries
  observability/  optional LangWatch SDK setup (unused when LANGWATCH_DISABLED=true)
tests/            pytest
run_query.py      edit QUERY and run
```
