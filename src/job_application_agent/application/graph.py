from langgraph.graph import END, START, StateGraph

from job_application_agent.application.nodes import (
    decide_next_action,
    enforce_step_budget,
    execute_action,
    inspect_page,
    open_application,
    pause_for_user,
)
from job_application_agent.application.routing import (
    route_after_budget,
    route_after_decision,
    route_after_inspection,
    route_after_pause,
)
from job_application_agent.application.state import WorkflowState

builder = StateGraph(WorkflowState)
builder.add_node("open", open_application)
builder.add_node("inspect", inspect_page)
builder.add_node("decide", decide_next_action)
builder.add_node("execute", execute_action)
builder.add_node("budget", enforce_step_budget)
builder.add_node("pause", pause_for_user)
builder.add_edge(START, "open")
builder.add_edge("open", "inspect")
builder.add_conditional_edges(
    "inspect", route_after_inspection, {"pause": "pause", "decide": "decide"}
)
builder.add_conditional_edges(
    "decide", route_after_decision, {"execute": "execute", "pause": "pause", "end": END}
)
builder.add_edge("execute", "budget")
builder.add_conditional_edges(
    "budget", route_after_budget, {"pause": "pause", "inspect": "inspect"}
)
builder.add_conditional_edges(
    "pause", route_after_pause, {"end": END, "inspect": "inspect"}
)
graph = builder.compile()
