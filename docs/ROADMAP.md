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

### Phase 5 ✅ — WhatsApp channel (Twilio Sandbox)
- Twilio WhatsApp Sandbox webhook (`POST /whatsapp/webhook`), same `BaseChannel`
  adapter pattern as Telegram
- Synchronous TwiML reply (`MessagingResponse`) — no outbound API calls/credentials
- `session_id = whatsapp_{phone}`, phone number doubles as the cross-channel
  Customer Identity key
- Adapter: `backend/app/channels/whatsapp/adapter.py`
- Reuses the `make cloudflare` tunnel; webhook URL registered manually in the
  Twilio Sandbox console

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

## Phase 7 ✅ — Unified Customer Identity, WhatsApp (Twilio), Agent Briefing, Sentiment Alerts

Implemented (2026-06-10), addressing team review feedback: the MVP needs to
tell an "unified omnichannel customer engagement" story — a single customer
identity across channels, real cross-channel context, and an employee
dashboard that briefs agents instead of just showing metrics. Given ~24h
remaining, one architectural change (phone number as the universal customer
key) unlocks most of this with minimal scope. See `feedback.txt` for the full
team review and prioritization discussion.

Decisions already made:
- Voice emotion detection started text-transcript-based (reuses
  `sentiment.py`); real prosody/audio-based emotion analysis followed as a
  closed follow-up (2026-06-11) — see below.
- Web chat asks for a phone number on first load ("soft login"); a "link
  existing channel" flow → tech debt.
- Twilio Voice (real phone calls) is P1, after this P0 lands.

### 1. DB schema — `backend/app/models.py`
- New `Customer` table: `id, phone (unique), name, language, created_at`
- `User.customer_id` → FK to `customers.id`, nullable
- `Message.user_id` → FK to `users.id`, nullable (enables cross-channel joins
  without parsing `session_id`)
- No Alembic — apply via `make fclean && make bup && make seed` (existing
  documented tech debt; local dev/demo data only)

### 2. `app/schemas.py`
- `IncomingMessage.phone: str | None = None`
- New `TicketUpdate(BaseModel)` with `status: Literal[...]` for ticket updates

### 3. New `backend/app/agent/identity.py`
- `resolve_user(db, session_id, channel, phone, language) -> User`
- Reuses the `session_id.split("_", 1)[1]` parsing currently duplicated in
  `tools.py::create_ticket`; find-or-create `User`, and find-or-create
  `Customer(phone=...)` + link `user.customer_id` when a phone is known
  (closes "Users table not populated for general inquiries" tech debt)

### 4. `backend/app/agent/core.py`
- Call `resolve_user()` in the existing persistence block, set `user_id` on
  both `Message` rows (user + agent turns)

### 5. New `backend/app/agent/briefing.py`
- `generate_briefing(history) -> {"summary", "urgency": low|medium|high,
  "recommended_action"}` via GPT-4o-mini JSON mode, same defensive pattern as
  `classify_sentiment`

### 6. WhatsApp adapter — `backend/app/channels/whatsapp/adapter.py`
- Twilio WhatsApp Sandbox, `BaseChannel` pattern like Telegram
- `POST /whatsapp/webhook` (form-encoded `From`/`Body`), reply via TwiML
  `MessagingResponse` (no outbound API calls / credentials needed for P0)
- `session_id = whatsapp_{phone}`, `phone` set on `IncomingMessage`
- Add `twilio` to `requirements.txt`; register router in `channels_main.py`
- Reuses the existing `make cloudflare` tunnel (already proxies `channels:8001`)
  — register `https://<tunnel>.trycloudflare.com/whatsapp/webhook` in the
  Twilio Sandbox console manually (no setup API like Telegram's)
- Remove unused Meta-oriented `whatsapp_token` / `whatsapp_phone_number_id` /
  `whatsapp_verify_token` from `config.py` / `.env.example`

### 7. Phone capture — web chat & voice
- `Chat.jsx`: "phone gate" screen on first load (stored in
  `localStorage['moei_phone']`), sent as `?phone=` on the WS connection and in
  the voice `FormData`; "New Chat" resets `session_id` but keeps the phone
- `webchat/adapter.py`: read `phone` from WS query params
- `voice/adapter.py`: add `phone: str | None = Form(None)`

### 8. Dashboard backend — `backend/app/dashboard/metrics.py`
- `GET /api/customers` — customers with ≥1 message, sorted by last activity
- `GET /api/customers/{id}/briefing` — cross-channel history + tickets +
  `generate_briefing()` output
- `PATCH /api/tickets/{id}` (`TicketUpdate`) — update status (+ `escalate=True`
  when status becomes `escalated`)
- Extend `GET /api/copilot` with resolved `customer_id`/`phone` per suggestion

### 9. Dashboard frontend — `frontend/src/components/Dashboard.jsx`
- Alerts banner: negative-sentiment co-pilot suggestions, "View Customer" link
- New "Customer 360" section: customer list (left) + briefing panel (right)
  with urgency badge, AI summary, recommended action, cross-channel timeline,
  ticket action buttons (In Progress / Resolve / Escalate)
- New CSS in `frontend/src/index.css` following existing variable/class
  conventions

### 10. Docs
- `CLAUDE.md`: `phone` in `IncomingMessage`, `customers` table in DATA RULES,
  Phase 5 ✅, WhatsApp via Twilio (not Meta Cloud API)
- `docs/DECISIONS.md`: mark cross-channel identity & WhatsApp as DECIDED;
  add OPEN/DEFERRED entries for prosody-based emotion detection and
  "link existing channel" flow
- `docs/ROADMAP.md`: mark Phase 5 done (Twilio details), remove "Users table
  not populated" tech debt, add new tech debt items below
- Remove stray `CLAUDE.md.backup`

### Follow-up (closed 2026-06-10)
Three quick wins identified during tech-debt review, all shipped:
- **Telegram phone capture**: `/start` sends a one-tap "Share phone number"
  button (`request_contact`); the shared contact links the Telegram `User`
  to the same `Customer` as WhatsApp/web chat — closes the cross-channel gap
  for the last channel.
- **Redis AOF persistence**: `redis-server --appendonly yes` +
  `redis_data` volume — live sessions survive a container restart.
- **Twilio webhook signature verification**: `/whatsapp/webhook` validates
  `X-Twilio-Signature` against `TWILIO_AUTH_TOKEN` when set (optional —
  sandbox demo works unchanged without it).

### Follow-up (closed 2026-06-11)
- **Real prosody/audio-based voice emotion detection**: new
  `agent/prosody.py` decodes the voice recording via `ffmpeg` (already in
  the image) and computes RMS loudness + autocorrelation pitch (F0) with
  `numpy`, classifying a coarse `tone: agitated | calm | flat`. Runs in
  parallel with Whisper STT in `voice/adapter.py`, stored on `Message.voice_tone`,
  surfaced in `/api/copilot` and `/api/customers/{id}/briefing` (and fed into
  the AI briefing prompt), and shown as a badge in the dashboard. See
  `docs/DECISIONS.md` for the heuristic-vs-ML trade-off.

### Verification
1. Update models, `make fclean && make bup && make seed`
2. `make ps` — all health checks green
3. Web chat: phone gate on clean browser, chat works as before
4. Message WhatsApp sandbox with the same phone as step 3 → `/api/customers`
   shows one customer with `webchat` + `whatsapp` channels
5. `/api/customers/{id}/briefing` returns cross-channel history + non-empty briefing
6. Negative-sentiment message → alerts banner shows it, "View Customer" opens
   the right briefing
7. Ticket action buttons update `/api/metrics` counts
8. `make test` still passes (`phone` optional everywhere)

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

#### Cross-channel identity linking beyond phone number
- Identity linking now works when the customer provides the *same* phone
  number on every channel (Phase 7), including Telegram via a one-tap
  `request_contact` button on `/start` (closed 2026-06-10). A customer who
  starts on web chat without a phone, or uses a *different* number on another
  channel, still gets a separate `User`/history with no link.
- **Fix:** "Link my WhatsApp/Telegram" flow — e.g. a one-time code sent via
  the new channel that the customer enters on the existing one, merging
  `User` rows under one `Customer`.
- **Effort:** ~2h

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

#### Twilio Voice (real phone calls)
- P1 from the team review: TwiML voice webhook + Twilio's STT/Gather → agent
  → TTS `Say`, reusing the same phone-based `Customer`/session context as
  WhatsApp.
- **Effort:** ~3h

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
