"""
LangGraph agent for the HCP Log Interaction Screen.

The graph implements a simple ReAct loop:
  START -> agent (LLM decides: respond directly, or call a tool)
        -> tools (executes tool, returns result to agent)
        -> agent (loop until LLM produces a final text answer)
        -> END

The agent is the reasoning core of the "AI Assistant" chat panel shown in the
UI mock: a rep types something like "Met Dr. Smith, discussed Product X
efficacy, positive sentiment, shared brochure" and the agent decides which
tool(s) to call (typically `log_interaction`), then confirms back to the rep.
"""
from typing import Annotated, TypedDict
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langchain_core.messages import SystemMessage

from app.agent.llm import get_llm
from app.agent.tools import ALL_TOOLS

SYSTEM_PROMPT = """You are the AI Assistant embedded in a pharma field rep's CRM, on the
"Log HCP Interaction" screen. Your job: help reps log, edit, and review interactions with
Healthcare Professionals (HCPs) via natural conversation, using your tools.

Guidelines:
- If the rep describes an interaction in free text, call `log_interaction` with that text.
- If they ask to change something about an existing interaction, call `edit_interaction`.
- If they ask about past visits/history with an HCP, call `search_hcp_history`.
- If they want a reminder or next visit scheduled, call `schedule_followup`.
- After logging an interaction, you may call `suggest_next_best_action` to propose follow-ups.
- Always confirm back to the rep in plain, concise language what was logged/changed.
- Never fabricate HCP data that wasn't in the rep's message.
"""


class AgentState(TypedDict):
    messages: Annotated[list, add_messages]


def build_agent_graph():
    llm = get_llm(temperature=0.2)
    llm_with_tools = llm.bind_tools(ALL_TOOLS)

    def agent_node(state: AgentState):
        messages = state["messages"]
        if not any(isinstance(m, SystemMessage) for m in messages):
            messages = [SystemMessage(content=SYSTEM_PROMPT)] + messages
        response = llm_with_tools.invoke(messages)
        return {"messages": [response]}

    def should_continue(state: AgentState):
        last_message = state["messages"][-1]
        if getattr(last_message, "tool_calls", None):
            return "tools"
        return END

    tool_node = ToolNode(ALL_TOOLS)

    graph = StateGraph(AgentState)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", tool_node)
    graph.set_entry_point("agent")
    graph.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
    graph.add_edge("tools", "agent")

    return graph.compile()


# Compiled once, reused across requests
agent_executor = build_agent_graph()
