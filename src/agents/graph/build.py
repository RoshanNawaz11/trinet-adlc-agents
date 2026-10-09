"""
    START → orchestrator ─┬─▶ planner ───────────────┐
                          ├─▶ validation ────────────┤
                          ├─▶ compliance ────────────┤  several can run at once;
                          ├─▶ payroll-calculation ───┤  each returns to the orchestrator
                          ├─▶ fetch (execution) ─────┤
                          ├─▶ review (pause, once) ──┤
                          ├─▶ execution ─────────────┘
                          └─ plan finished ─────────────▶ END

"""

from langgraph._internal._retry import default_retry_on
from langgraph.graph import END, START, StateGraph
from langgraph.types import RetryPolicy

from agents.graph.edges import AGENTS, route_from_orchestrator
from agents.graph.interrupts import review_node
from agents.graph.states import State
from agents.nodes.compliance.node import compliance_node
from agents.nodes.execution.fetch import fetch_node
from agents.nodes.execution.node import execution_node
from agents.nodes.orchestrator.node import OrchestratorError, orchestrator_node
from agents.nodes.payroll_calculation.node import payroll_calculation_node
from agents.nodes.planner.node import PlannerOutputError, planner_node
from agents.nodes.stage_agent import AgentOutputError
from agents.nodes.validation.node import validation_node
from agents.runtime.checkpointer import get_checkpointer
from json_utils import JSONParseError

# An answer the model got wrong (no JSON, wrong shape, a route the guardrails
# refused) is worth asking for again: the next answer usually differs. These are
# ValueErrors, which LangGraph's default never retries.
_MODEL_OUTPUT_ERRORS = (JSONParseError, AgentOutputError, PlannerOutputError, OrchestratorError)


def _retry_on(exc: Exception) -> bool:
    return isinstance(exc, _MODEL_OUTPUT_ERRORS) or default_retry_on(exc)


_RETRY = RetryPolicy(max_attempts=3, retry_on=_retry_on)


def build_graph(checkpointer_kind: str = "memory"):
    graph = StateGraph(State)

    graph.add_node("orchestrator", orchestrator_node, retry_policy=_RETRY)
    graph.add_node("planner", planner_node, retry_policy=_RETRY)
    graph.add_node("validation", validation_node, retry_policy=_RETRY)
    graph.add_node("compliance", compliance_node, retry_policy=_RETRY)
    graph.add_node("payroll-calculation", payroll_calculation_node, retry_policy=_RETRY)
    graph.add_node("execution", execution_node, retry_policy=_RETRY)
    graph.add_node("fetch", fetch_node, retry_policy=_RETRY)
    graph.add_node("review", review_node)

    graph.add_edge(START, "orchestrator")
    graph.add_conditional_edges(
        "orchestrator",
        route_from_orchestrator,
        ["planner", *AGENTS, "fetch", "review", END],
    )
    for node in ("planner", *AGENTS, "fetch", "review"):
        graph.add_edge(node, "orchestrator")

    return graph.compile(checkpointer=get_checkpointer(checkpointer_kind))
