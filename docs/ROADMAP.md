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

### Phase 4 ✅ — Voice channel
- POST `/voice/message` on channels service (port 8001)
- STT: OpenAI Whisper API (`openai.audio.transcriptions`)
- Agent: same `run_agent()` — no changes (channel-agnostic)
- TTS: OpenAI TTS API (model=tts-1, voice configurable via `TTS_VOICE` env)
- Browser mic button (🎤/⏹) in web chat using MediaRecorder API
- Audio response played in-browser from base64
- Messages stored in DB as `channel="voice"`

### Phase 5 ⬜ — WhatsApp channel
- Meta Cloud API webhook
- Same adapter pattern as Telegram
- Adapter: `backend/app/channels/whatsapp/adapter.py`
- Verify token handshake (GET + POST)

### Phase 6 ✅ — Polish: sentiment, co-pilot, tests, demo prep
- **Sentiment analysis:** GPT-4o-mini classifier (`positive` / `neutral` / `negative`)
  - `backend/app/agent/sentiment.py`
  - Stored in `Message.sentiment` column
  - Displayed as pie chart in dashboard
- **AI co-pilot panel:** `GET /api/copilot` — live feed of recent conversations + AI-suggested replies for human agents
- **Sentiment chart:** third chart in dashboard (3-column responsive grid)
- **Integration tests:** `tests/test_health.py` (5 tests), `tests/test_agent.py` (5 tests)
  - `make test` — runs via `docker compose exec` with correct container URLs
- **Demo seed script:** `scripts/seed_demo.py` — 8 realistic conversations, EN + AR, multiple channels
  - `make seed`

---

## Test coverage

| File | Tests |
|------|-------|
| `tests/test_health.py` | backend health, channels health, frontend up, metrics shape, copilot shape |
| `tests/test_agent.py` | agent response, sentiment field, Arabic response, ticket creation, session history |

Run with: `make test`

---

## Tech debt

### 🔴 High — fix before production

#### WebSocket has no authentication
- Any client knowing a `session_id` can connect and inject or read messages
- **Fix:** JWT or signed token on the WebSocket handshake
- **Effort:** ~2h

### 🟡 Medium — fix before wider rollout

#### Cross-channel identity linking
- Same person on Telegram (`telegram_123`) and web chat (`webchat_abc`) has separate session histories with no link between them
- **Demo workaround:** Presenter manually enters the Telegram session ID in the web chat input
- **Fix:** `identities` table linking `(channel, channel_user_id)` pairs to a single internal `user_id`
- **Effort:** ~3h

#### Chat history fallback to DB missing
- `GET /api/session/{id}` reads from Redis only
- If Redis restarts or TTL expires, history is lost — even though messages exist in the `messages` table
- **Fix:** Fall back to `SELECT * FROM messages WHERE session_id = ? ORDER BY timestamp` when Redis key is missing
- **Effort:** ~1h

#### Alembic migrations not configured
- Schema changes require `make fclean && make bup` (drops all data)
- **Fix:** Initialize Alembic, write initial migration from current models
- **Effort:** ~1h

### 🟢 Low — nice to have

#### Users table not populated for general inquiries
- `users` rows only created when `create_ticket` tool is called
- **Fix:** Upsert a user row on every first message in a session
- **Effort:** ~30min

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

1. **Arabic inquiry via Telegram**
   - Customer: "أريد الإبلاغ عن انقطاع في الكهرباء"
   - Agent replies in Arabic, creates a ticket

2. **Same customer opens web chat — context already there**
   - Show same session_id in both channels
   - Agent remembers the previous conversation

3. **Customer uses voice — browser mic**
   - Click 🎤, speak, agent replies in audio

4. **Human agent co-pilot**
   - Dashboard co-pilot panel shows the live conversation
   - AI-suggested replies visible in real time

5. **Leadership view**
   - Dashboard: active sessions, ticket counts, escalated cases, sentiment breakdown, channel breakdown
