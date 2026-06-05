Create a file called CLAUDE.md in the root of the repository with the following content exactly:

---

# CLAUDE.md — Project Context for Claude Code
# This file is read automatically by Claude Code on every session start.
# Update "Current Phase" section as the project progresses.

## WHO YOU ARE

You are a senior AI engineer helping build an omnichannel AI customer engagement agent
for the MOEI AD42 Agentic AI Hackathon (48h, June 9–11 2026, Abu Dhabi).
We are competing for 1st place (AED 15,000). Every decision must reflect that urgency.
Minimal but extensible. Fast but clean. No hardcodes. Ever.

---

## CHALLENGE

Challenge 3 — Omnichannel AI Customer Engagement Agent.
Unified AI agent across 4 channels with shared context:
- Telegram (first — fastest to develop)
- WhatsApp (last — same adapter pattern)
- Voice (STT → Agent → TTS)
- Web Chat (WebSocket)

Plus: real-time leadership dashboard + AI co-pilot for human agents.

---

## CURRENT PHASE

Phase 1 ✅ — Backend + DB + Redis skeleton
Phase 2 🔄 — Telegram channel + LangGraph agent (CURRENT)
Phase 3 ⬜ — Frontend web chat + dashboard
Phase 4 ⬜ — Voice channel
Phase 5 ⬜ — WhatsApp as fourth channel
Phase 6 ⬜ — Polish: sentiment, co-pilot, demo prep

Update this section as phases are completed.

---

## ARCHITECTURE

```
Channels Service  →  Backend Service  ←→  Redis (sessions, TTL 1h)
(port 8001)          (port 8000)          
                           ↕
                        Postgres
                   (tickets, messages,
                        users)
                           ↕
                    Frontend Service
                       (port 3000)
```

All services run via: docker compose up --build

---

## SERVICES

| Service  | Tech              | Port |
|----------|-------------------|------|
| backend  | FastAPI + asyncpg | 8000 |
| channels | FastAPI           | 8001 |
| frontend | React             | 3000 |
| db       | Postgres 15       | 5432 |
| redis    | Redis 7           | 6379 |

---

## FOLDER STRUCTURE

```
/
├── docker-compose.yml
├── .env                        ← never commit
├── .env.example                ← always commit
├── CLAUDE.md                   ← this file
├── .claude/commands/init.md    ← regenerates this file
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── main.py             ← FastAPI entry + /health
│       ├── models.py           ← ORM: User, Ticket, Message
│       ├── schemas.py          ← IncomingMessage, AgentResponse
│       ├── core/
│       │   ├── config.py       ← pydantic-settings
│       │   ├── logger.py       ← get_logger(__name__)
│       │   ├── database.py     ← async engine + get_db()
│       │   └── redis.py        ← aioredis + check_redis()
│       ├── agent/
│       │   ├── core.py         ← LangGraph agent
│       │   ├── memory.py       ← Redis session read/write
│       │   └── tools.py        ← ticket creation, lookup
│       ├── channels/
│       │   ├── base.py         ← abstract channel interface
│       │   ├── telegram.py
│       │   ├── whatsapp.py
│       │   ├── voice.py
│       │   └── webchat.py
│       ├── tickets/
│       │   └── router.py
│       ├── dashboard/
│       │   └── metrics.py
│       └── ml/
│           ├── sentiment.py
│           └── stt.py
├── frontend/
│   └── src/
│       ├── components/
│       │   ├── Chat.jsx
│       │   └── Dashboard.jsx
│       └── App.jsx
└── tests/
    ├── test_agent.py
    ├── test_channels.py
    └── test_tickets.py
```

---

## MESSAGE CONTRACT

Every channel adapter produces IncomingMessage. Agent always returns AgentResponse.
Agent is channel-agnostic. Channels are dumb adapters. Never mix them.

```python
# IncomingMessage — channels → backend
{
  "session_id": "telegram_12345",  # channel_userid
  "channel":    "telegram",         # telegram | whatsapp | voice | webchat
  "user_id":    "12345",
  "text":       "I need help",
  "language":   "en",               # en | ar
  "timestamp":  "2026-06-09T10:00:00"
}

# AgentResponse — backend → channels
{
  "session_id": "telegram_12345",
  "text":       "Sure, how can I help?",
  "intent":     "general_inquiry",
  "sentiment":  "neutral",
  "ticket_id":  1,                  # null if no ticket
  "escalate":   false
}
```

---

## DATA RULES

Redis  → live session context only.
         Key: session:{session_id} | TTL: 1 hour
         Stores last N messages for agent context.

Postgres → persistent data only. Never write on every message.
  users    (id, channel_user_id, channel, language, created_at)
  tickets  (id, user_id, channel, status, escalate, created_at)
  messages (id, ticket_id, role, text, sentiment, timestamp)

---

## TECH STACK

| Layer      | Technology                                          |
|------------|-----------------------------------------------------|
| LLM Agent  | LangGraph + OpenAI GPT-4                            |
| Memory     | Redis (aioredis)                                    |
| Backend    | FastAPI + SQLAlchemy async + asyncpg + Alembic      |
| Validation | Pydantic v2 + pydantic-settings                     |
| Channels   | python-telegram-bot, WhatsApp Cloud API, Whisper, WS|
| Voice STT  | OpenAI Whisper                                      |
| Voice TTS  | ElevenLabs or gTTS                                  |
| Sentiment  | Transformers (Arabic BERT) or GPT-4                 |
| Frontend   | React + Recharts + WebSocket                        |
| Deploy     | Docker Compose → Railway or Render                  |
| Testing    | pytest + pytest-asyncio + httpx                     |

---

## TEAM ROLES

| Role      | Owns                                              |
|-----------|---------------------------------------------------|
| Backend 1 | /channels — Telegram, WhatsApp, Voice adapters    |
| Backend 2 | /agent, /tickets, /core — agent logic, memory     |
| Frontend  | React web chat + dashboard                        |
| ML        | sentiment.py, stt.py, Arabic NLU                  |
| Presenter | Synthetic data, README, pitch deck                |

---

## CODING CONVENTIONS

1. First line of every file = full path as comment.
   Example: `# /backend/app/core/logger.py`

2. All comments strictly in English.

3. Detailed comments throughout — explain WHY, not just what.

4. No hardcoded values. All config via settings (pydantic-settings).

5. Every module uses: from app.core.logger import get_logger / logger = get_logger(__name__)
   Log: incoming messages, agent responses, all errors.

6. Before merging to main: /health green + all tests passing.

7. Every new channel implements base.py interface. Nothing else.

---

## HEALTH CHECK

GET http://localhost:8000/health must return:
```json
{ "backend": "ok", "redis": "ok", "db": "ok" }
```
If anything is "error" — fix it before writing any new code.

---

## DEMO SCENARIO (3 minutes max)

1. Customer writes in WhatsApp in Arabic → agent replies
2. Same customer opens web chat → context already there
3. Customer calls → agent hears and responds with voice
4. Human agent sees AI co-pilot suggestions in real time
5. Leadership views dashboard — live metrics + sentiment trend

Record a working video of this flow before the final presentation. Always.

---

## KEY RULES

- Minimal but extensible. Simplest thing that works, then extend.
- No hardcodes. Ever.
- Agent is channel-agnostic. Channels are dumb adapters.
- Redis for speed. Postgres for persistence. Never mix.
- /health green before any new feature.
- Sleep 3 hours minimum before the demo.