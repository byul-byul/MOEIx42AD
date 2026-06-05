# /backend/app/agent/core.py
import operator
import re
from typing import Annotated, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph

from app.agent.tools import channel_ctx, create_ticket, get_ticket_status, session_ctx
from app.core.config import settings
from app.core.logger import get_logger
from app.core.redis import get_session, save_session
from app.schemas import AgentResponse, IncomingMessage

logger = get_logger(__name__)

SYSTEM_PROMPT = """You are a bilingual (English / Arabic) AI customer service agent for MOEI —
the Ministry of Energy and Infrastructure of Abu Dhabi, UAE.

You help customers with:
- Electricity and water service inquiries
- Bill payments and account information
- Service connection requests and outages
- Meter readings and technical issues
- General ministry services and procedures

Guidelines:
- Reply in the same language the customer uses (Arabic or English).
- Be polite, professional, and concise.
- If the customer reports a problem or needs follow-up, use the create_ticket tool.
- If the customer provides a ticket number, use get_ticket_status to check it.
- For urgent safety issues (gas leaks, electrical hazards, fires), advise calling emergency services immediately.
- Do not invent information. If unsure, offer to create a ticket for the relevant team.
"""

_ESCALATION_KEYWORDS = [
    "gas leak", "electrical hazard", "fire", "emergency",
    "تسرب غاز", "حريق", "خطر كهربائي", "طوارئ",
]

TOOLS = [create_ticket, get_ticket_status]
_tools_map = {t.name: t for t in TOOLS}

_llm = ChatOpenAI(
    model="gpt-4o",
    temperature=0.3,
    api_key=settings.openai_api_key,
).bind_tools(TOOLS)


class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], operator.add]


def _should_continue(state: AgentState) -> str:
    last = state["messages"][-1]
    if getattr(last, "tool_calls", None):
        return "tools"
    return END


async def _llm_node(state: AgentState) -> dict:
    response = await _llm.ainvoke(state["messages"])
    return {"messages": [response]}


async def _tool_node(state: AgentState) -> dict:
    results = []
    for tc in state["messages"][-1].tool_calls:
        fn = _tools_map.get(tc["name"])
        if fn is None:
            content = f"Unknown tool: {tc['name']}"
        else:
            try:
                content = await fn.ainvoke(tc["args"])
            except Exception as exc:
                logger.error("Tool %s failed: %s", tc["name"], exc)
                content = f"Tool error: {exc}"
        results.append(ToolMessage(content=str(content), tool_call_id=tc["id"]))
    return {"messages": results}


_builder = StateGraph(AgentState)
_builder.add_node("llm", _llm_node)
_builder.add_node("tools", _tool_node)
_builder.set_entry_point("llm")
_builder.add_conditional_edges("llm", _should_continue, {"tools": "tools", END: END})
_builder.add_edge("tools", "llm")
_agent = _builder.compile()


def _extract_ticket_id(messages: list[BaseMessage]) -> int | None:
    for msg in messages:
        if isinstance(msg, ToolMessage):
            m = re.search(r"Ticket #(\d+)", msg.content)
            if m:
                return int(m.group(1))
    return None


def _is_escalation(text: str) -> bool:
    lower = text.lower()
    return any(kw.lower() in lower for kw in _ESCALATION_KEYWORDS)


async def run_agent(msg: IncomingMessage) -> AgentResponse:
    """Run the LangGraph agent for one incoming message and return a structured response."""
    session_ctx.set(msg.session_id)
    channel_ctx.set(msg.channel)

    # Reconstruct message history from Redis
    history = await get_session(msg.session_id)
    past: list[BaseMessage] = []
    for h in history:
        if h["role"] == "user":
            past.append(HumanMessage(content=h["text"]))
        else:
            past.append(AIMessage(content=h["text"]))

    input_messages = [SystemMessage(content=SYSTEM_PROMPT)] + past + [HumanMessage(content=msg.text)]

    logger.info("Agent invoked | session=%s | text=%.80s", msg.session_id, msg.text)
    result = await _agent.ainvoke({"messages": input_messages})

    reply_text = result["messages"][-1].content
    ticket_id = _extract_ticket_id(result["messages"])
    escalate = _is_escalation(msg.text) or _is_escalation(reply_text)

    # Persist conversation turn to Redis
    await save_session(
        msg.session_id,
        history + [
            {"role": "user", "text": msg.text},
            {"role": "agent", "text": reply_text},
        ],
    )

    intent = "support_request" if ticket_id else "general_inquiry"
    logger.info("Agent done | session=%s | intent=%s | ticket=%s | escalate=%s",
                msg.session_id, intent, ticket_id, escalate)

    return AgentResponse(
        session_id=msg.session_id,
        text=reply_text,
        intent=intent,
        sentiment="neutral",
        ticket_id=ticket_id,
        escalate=escalate,
    )
