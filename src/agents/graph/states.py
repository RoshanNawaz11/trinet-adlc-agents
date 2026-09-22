from typing import Annotated, Any, Literal, NotRequired, TypedDict
import operator

# planner agent state
class Step(TypedDict):
    step_id: str
    skill: Literal["summarize", "classify"]
    input: dict[str, Any]
    status: Literal["pending", "running", "done", "bounced", "failed"]
    attempt: int

# planner agent result
class StepResult(TypedDict):
    step_id: str
    agent: Literal["expert", "worker"]
    output: dict[str, Any]
    confidence: NotRequired[float]
    escalation: NotRequired[dict[str, Any]]
    error: NotRequired[str]


#generic for all the agents
class State(TypedDict):
    schema_version: int
    run_id: str                 # LangGraph thread_id stays in config
    query: str
    status: Literal["running", "needs_review", "done", "failed"]
    flagged: bool               # interrupt / human review
    mcp_results: NotRequired[list[dict[str, Any]]]  # orchestrator tool calls, for later steps
    plan: NotRequired[list[Step]]
    step_results: Annotated[list[StepResult], operator.add]
    final_output: NotRequired[dict[str, Any]]
    error: NotRequired[str]