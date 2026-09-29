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
