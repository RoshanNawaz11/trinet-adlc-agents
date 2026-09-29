from datetime import UTC, datetime
from typing import Annotated, Any, Literal, NotRequired, TypedDict
import operator

Stage = Literal["planning", "validation", "compliance", "payroll", "execution"]


# one step of the planner's plan: which agent runs, and what to focus on
class PlanStep(TypedDict):
    agent: str                  # a graph node name, e.g. "validation"
    task: str


# one row of the case timeline the UI shows
class StepRecord(TypedDict):
    stage: Stage
    agent: str
    title: str
    source: str                 # system the step read from, e.g. "MCP · get_service_order"
    at: str                     # ISO-8601 UTC
    result: NotRequired[str]
    evidence: NotRequired[dict[str, Any]]


# an issue a human must decide on before execution runs
class Flag(TypedDict):
    flag_id: str
    type: str                   # e.g. "duplicateSO", "complianceTiming", "netPayMismatch"
    stage: Stage
    title: str
    detail: dict[str, Any]
    resolved: bool
    decisions: list[dict[str, Any]]  # every decision taken on it, declines included


# what the reviewer sends on resume
class Decision(TypedDict):
    action: Literal["confirm", "decline"]
    flag_id: NotRequired[str]
    value: NotRequired[Any]     # e.g. the chosen option
    reason: NotRequired[str]    # required for decline


def merge_flags(current: list[Flag], new: list[Flag]) -> list[Flag]:
    """Each agent adds its own flags; review sends back an updated copy of
    one. A flag with a known flag_id replaces it in place."""
    by_id = {f["flag_id"]: f for f in current}
    by_id.update({f["flag_id"]: f for f in new})
    return list(by_id.values())


#generic for all the agents
class State(TypedDict):
    schema_version: int
    run_id: str                 # LangGraph thread_id stays in config
    service_order_id: NotRequired[str]
    service_order: NotRequired[dict[str, Any]]  # the record fetched by id before the run starts
    query: NotRequired[str]     # fallback: the order described as text, when no id is given
    status: Literal["running", "needs_review", "done", "failed"]
    plan: NotRequired[list[PlanStep]]  # the planner's plan; the orchestrator runs it in order
    flagged: bool               # an unresolved flag is waiting for human review
    priority: NotRequired[Literal["high", "medium", "low"]]  # planner's decision, raised a level once any flag is raised
    confidence: NotRequired[int]  # 0-100: the lowest stage confidence, once a stage has reported
    mcp_results: NotRequired[list[dict[str, Any]]]  # MCP tool calls, for later agents
    results: Annotated[dict[str, dict[str, Any]], operator.or_]  # agent name -> its output (planner: its plan + priority)
    steps: Annotated[list[StepRecord], operator.add]
    flags: Annotated[list[Flag], merge_flags]
    final_output: NotRequired[dict[str, Any]]
    error: NotRequired[str]


def step_record(stage: Stage, agent: str, title: str, source: str, **extra: Any) -> StepRecord:
    return {
        "stage": stage,
        "agent": agent,
        "title": title,
        "source": source,
        "at": datetime.now(UTC).isoformat(),
        **extra,
    }
