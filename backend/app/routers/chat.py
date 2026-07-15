import json
from fastapi import APIRouter
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage

from app.agent.graph import agent_executor
from app.schemas import ChatRequest, ChatResponse

router = APIRouter(prefix="/api/chat", tags=["chat"])

# Simple in-memory session store (swap for Redis/DB in production)
_SESSIONS: dict[str, list] = {}


@router.post("/", response_model=ChatResponse)
def chat(payload: ChatRequest):
    """
    Conversational path for the 'Log HCP Interaction' AI Assistant panel.
    The LangGraph agent decides which tool(s) to invoke (log_interaction,
    edit_interaction, search_hcp_history, schedule_followup,
    suggest_next_best_action) based on the rep's free-text message.
    """
    history = _SESSIONS.get(payload.session_id, [])
    history.append(HumanMessage(content=payload.message))

    result = agent_executor.invoke({"messages": history})
    messages = result["messages"]
    _SESSIONS[payload.session_id] = messages

    tool_calls_made = [
        m.name for m in messages if isinstance(m, ToolMessage)
    ]

    final_reply = ""
    for m in reversed(messages):
        if isinstance(m, AIMessage) and m.content:
            final_reply = m.content
            break

    return ChatResponse(reply=final_reply, tool_calls=tool_calls_made)
