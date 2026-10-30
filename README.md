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

Model calls go directly to the Anthropic API using the official Python SDK. Configure with `ANTHROPIC_API_KEY` (required) and optionally `ANTHROPIC_BASE_URL` to override the default endpoint.

Chat, the MCP tool loop, running Skills, and code execution all use one client in
`src/agents/model/gateway.py`. `require_client()` and `require_skills_client()` return that same
client, so skill uploads (list, create, new version) use the Anthropic API directly as well.
Without `ANTHROPIC_API_KEY`, `ModelGateway` raises `MissingAPIKeyError`.

Models per node are set in `src/agents/model/policy.yaml`.

## Observability

LangWatch provides agent-side tracing. Enable with `LANGWATCH_DISABLED=false` and configure `LANGWATCH_API_KEY` and `LANGWATCH_ENDPOINT_URL`.

Each run sets `session_id` (`gateway.py`, from `run_query` in `runtime/runner.py`). `traceparent()`
is stable for that session and `trace_id()` is returned on the run result, so one run's calls stay
together. Observability never blocks a run: if LangWatch is down or rejects the key, the request
still succeeds.

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
| `ANTHROPIC_API_KEY` | Required | Anthropic API key for model calls and skill uploads |
| `ANTHROPIC_BASE_URL` | Optional | Custom Anthropic endpoint (uses SDK default if unset) |
| `LANGWATCH_DISABLED` | Optional | Set to `false` to enable tracing (default: `false`) |
| `LANGWATCH_API_KEY` | Required (if tracing enabled) | LangWatch API key |
| `LANGWATCH_ENDPOINT_URL` | Required (if tracing enabled) | LangWatch endpoint |
| `MCP_SERVER` | you want MCP tools | e.g. `http://127.0.0.1:8080/mcp` |

Keep `.env` files that you `source` in WSL with **LF line endings**. CRLF puts a hidden carriage
return at the end of every value and causes `: command not found` errors and failed auth.

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| Model calls fail | If model calls fail, check that `ANTHROPIC_API_KEY` is set and valid. If using a custom `ANTHROPIC_BASE_URL`, verify the endpoint is reachable. |
| `MissingAPIKeyError` | `ANTHROPIC_API_KEY` is not set |
| Nothing in LangWatch | Confirm `LANGWATCH_DISABLED=false`, and that `LANGWATCH_API_KEY` and `LANGWATCH_ENDPOINT_URL` are set. Widen the time range in the project that owns the key. |
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
