# Roadmap — MOEI AI Customer Engagement Agent

---

## Phases

### Phase 1 ✅ — Backend + DB + Redis skeleton
- FastAPI backend (port 8000) with `/health` endpoint
- PostgreSQL 15: `users`, `tickets`, `messages` tables
- Redis 7: session management (TTL 1h, last 20 messages)
- Docker Compose: all 5 services
- Makefile: build/up/down/clean/fclean/bup/ps/logs

### Phase 2 ✅ — Telegram channel + LangGraph agent
- LangGraph ReAct agent (GPT-4o, temp 0.3)
- Tools: `create_ticket`, `get_ticket_status`
- Bilingual system prompt (EN/AR)
- Escalation detection (safety keywords)
- Telegram webhook adapter (python-telegram-bot 21)
- `make ngrok` + `make telegram-setup` automation
- Message persistence to DB

### Phase 3 ✅ — Frontend web chat + dashboard
- WebSocket channel (`/ws/{session_id}`)
- React web chat: history restore, typing indicator, New Chat button
- Operations dashboard: live metrics, bar + pie charts (Recharts), tickets table
- CORS, VITE env vars for backend URLs

### Phase 4 🔄 — Voice channel
- WebSocket or HTTP endpoint accepting audio upload
- STT: OpenAI Whisper (`requirements-ml.txt`)
- Agent: same `run_agent()` — no changes
- TTS: ElevenLabs (primary) or gTTS (fallback)
- Adapter: `backend/app/channels/voice/adapter.py`

### Phase 5 ⬜ — WhatsApp channel
- Meta Cloud API webhook
- Same adapter pattern as Telegram
- Adapter: `backend/app/channels/whatsapp/adapter.py`
- Verify token handshake (GET + POST)

### Phase 6 ⬜ — Polish: sentiment, co-pilot, demo prep
- Sentiment analysis: replace `"neutral"` placeholder with real model
  - Arabic: `CAMeL-Lab/bert-base-arabic-camelbert-mix-sentiment`
  - English: `distilbert-base-uncased-finetuned-sst-2-english`
- AI co-pilot panel in dashboard (suggested replies for human agents)
- Synthetic demo data seeding script
- Demo video recording
- Final health check and load test

---

## Planned test coverage (before Phase 6)

| File | What to test |
|------|-------------|
| `tests/test_health.py` | `/health` returns `ok` for all three services |
| `tests/test_agent.py` | `run_agent()` returns valid response; `create_ticket` tool creates DB row |
| `tests/test_channels.py` | Telegram adapter correctly parses Update → IncomingMessage |
| `tests/test_metrics.py` | `/api/metrics` returns correct counts after seeding data |

---

## Tech debt

### 🔴 High — fix before production

#### WebSocket has no authentication
- Any client knowing a `session_id` can connect and inject or read messages
- **Fix:** JWT or signed token on the WebSocket handshake
- **Effort:** ~2h

### 🟡 Medium — fix before wider rollout

#### Cross-channel identity linking
- Same person on Telegram (`telegram_123`) and web chat (`webchat_abc`) has separate session histories and separate DB rows with no link between them
- **Demo workaround:** Presenter manually enters the Telegram session ID in the web chat input
- **Fix:** `identities` table linking `(channel, channel_user_id)` pairs to a single internal `user_id`; update `run_agent()` to resolve identities on session start
- **Effort:** ~3h

#### Chat history fallback to DB missing
- `GET /api/session/{id}` reads from Redis only
- If Redis is restarted or TTL expires, history is lost — even though messages exist in the `messages` table
- **Fix:** Fall back to `SELECT * FROM messages WHERE session_id = ? ORDER BY timestamp` when Redis key is missing
- **Effort:** ~1h

#### Alembic migrations not configured
- Schema changes require `make fclean && make bup` (drops all data)
- **Fix:** Initialize Alembic (`alembic init`), write initial migration from current models
- **Effort:** ~1h

### 🟢 Low — nice to have

#### Users table not populated for general inquiries
- `users` rows only created when `create_ticket` tool is called
- Customers who only chat without reporting an issue are invisible in the DB
- **Fix:** Upsert a user row on every first message in a session
- **Effort:** ~30min

#### Sentiment analysis is a placeholder
- `AgentResponse.sentiment` always returns `"neutral"`
- `Message.sentiment` column always null
- **Fix:** Add sentiment inference in Phase 6 (see above)
- **Effort:** ~2h (model loading + inference integration)

#### Redis has no persistence
- Default Redis config is in-memory only; restart loses all active sessions
- **Fix:** Enable AOF or RDB persistence in `docker-compose.yml` redis config
- **Effort:** ~15min

#### No rate limiting
- `/api/message` and `/ws/` endpoints have no rate limiting
- One misbehaving client can spike OpenAI costs
- **Fix:** `slowapi` middleware with per-session limits
- **Effort:** ~1h

---

## Deployment targets

The stack is designed to deploy on **Railway** or **Render**:

- Each service (`backend`, `channels`, `frontend`) deploys as a separate web service
- `db` and `redis` as managed services (Railway has native Postgres + Redis)
- Environment variables injected via platform UI (replace `.env`)
- Telegram webhook URL = public service URL of the channels service

---

## Demo scenario (3 minutes)

For the hackathon presentation:

1. **Arabic inquiry via WhatsApp** *(Phase 5)*
   - Customer: "أريد الإبلاغ عن انقطاع في الكهرباء"
   - Agent replies in Arabic, creates a ticket

2. **Same customer opens web chat — context already there**
   - Show same session_id in both channels
   - Agent remembers the previous conversation

3. **Customer calls — voice response** *(Phase 4)*
   - Agent hears the question, responds with synthesized voice

4. **Human agent co-pilot** *(Phase 6)*
   - Dashboard shows the live conversation
   - AI suggests response options for the human agent

5. **Leadership view**
   - Dashboard: active sessions, ticket counts, escalated cases, channel breakdown
