# /backend/app/agent/core.py
import operator
import re
from typing import Annotated, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph

from app.agent.identity import normalize_phone, resolve_user
from app.agent.sentiment import classify_sentiment
from app.agent.tools import channel_ctx, create_ticket, get_ticket_status, session_ctx
from app.core.config import settings
from app.core.database import AsyncSessionFactory
from app.core.logger import get_logger
from app.core.redis import get_session, save_session
from app.models import ChannelType, Customer, Message, MessageRole, Ticket, TicketStatus
from sqlalchemy import select
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


def _memory_key(session_id: str, phone: str | None) -> str:
    """Redis key for the agent's conversational memory.

    When the customer's phone is known, every channel shares one memory key
    so the agent has real cross-channel context (Telegram, WhatsApp, web
    chat, voice all see the same running conversation). Without a phone,
    memory stays scoped to this channel's session.
    """
    if phone:
        return f"phone_{normalize_phone(phone)}"
    return session_id


async def run_agent(msg: IncomingMessage) -> AgentResponse:
    """Run the LangGraph agent for one incoming message and return a structured response."""
    session_ctx.set(msg.session_id)
    channel_ctx.set(msg.channel)
    channel_enum = ChannelType(msg.channel)

    # Resolve identity up front: even if this message itself carries no phone,
    # a previously-linked Customer's phone lets us share live conversation
    # memory across channels (see _memory_key). Reused below for persistence
    # so the user is only resolved/created once per turn.
    effective_phone = msg.phone
    user_id: int | None = None
    try:
        async with AsyncSessionFactory() as db:
            user = await resolve_user(db, msg.session_id, channel_enum, msg.phone, msg.language)
            await db.commit()
            user_id = user.id
            if not effective_phone and user.customer_id:
                customer = await db.get(Customer, user.customer_id)
                if customer:
                    effective_phone = customer.phone
    except Exception as exc:
        logger.error("Failed to resolve identity: %s", exc)

    memory_key = _memory_key(msg.session_id, effective_phone)

    # Reconstruct message history from Redis (shared cross-channel via phone)
    history = await get_session(memory_key)
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

    # Persist conversation turn to Redis (shared cross-channel via phone)
    await save_session(
        memory_key,
        history + [
            {"role": "user", "text": msg.text},
            {"role": "agent", "text": reply_text},
        ],
    )

    intent = "support_request" if ticket_id else "general_inquiry"
    sentiment = await classify_sentiment(msg.text)
    logger.info("Agent done | session=%s | intent=%s | ticket=%s | escalate=%s | sentiment=%s",
                msg.session_id, intent, ticket_id, escalate, sentiment)

    # Persist both turns + update ticket escalation flag if needed
    try:
        async with AsyncSessionFactory() as db:
            db.add(Message(
                ticket_id=ticket_id,
                user_id=user_id,
                session_id=msg.session_id,
                channel=channel_enum,
                role=MessageRole.user,
                text=msg.text,
                sentiment=sentiment,
                voice_tone=msg.voice_tone,
            ))
            db.add(Message(
                ticket_id=ticket_id,
                user_id=user_id,
                session_id=msg.session_id,
                channel=channel_enum,
                role=MessageRole.agent,
                text=reply_text,
            ))
            if escalate and ticket_id:
                result = await db.execute(select(Ticket).where(Ticket.id == ticket_id))
                ticket = result.scalar_one_or_none()
                if ticket:
                    ticket.escalate = True
                    ticket.status = TicketStatus.escalated
            await db.commit()
    except Exception as exc:
        logger.error("Failed to persist messages to DB: %s", exc)

    return AgentResponse(
        session_id=msg.session_id,
        text=reply_text,
        intent=intent,
        sentiment=sentiment,
        ticket_id=ticket_id,
        escalate=escalate,
    )
