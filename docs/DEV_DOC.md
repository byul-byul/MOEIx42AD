# Developer Documentation — MOEI AI Customer Engagement Agent

This guide covers environment setup, architecture details, and workflows for developers working on this project.

---

## Prerequisites

| Tool | Version | Install |
|------|---------|---------|
| Docker + Docker Compose | Latest | https://docs.docker.com/get-docker/ |
| Make | Any | Pre-installed on macOS/Linux |
| ngrok | Any | `brew install ngrok` |
| Python | 3.11+ | For local runs only (not required for Docker) |
| Node.js | 20+ | For local frontend runs only |

---

## Setup from scratch

```bash
# 1. Clone the repository
git clone https://github.com/byul-byul/MOEIx42AD.git
cd MOEIx42AD

# 2. Create environment file
cp .env.example .env
```

Edit `.env` — minimum required values:

```env
POSTGRES_PASSWORD=your_strong_password
OPENAI_API_KEY=sk-...
TELEGRAM_BOT_TOKEN=...     # from @BotFather
```

```bash
# 3. Authenticate ngrok (one-time)
ngrok config add-authtoken <your-ngrok-token>

# 4. Start everything
make bup
```

`make bup` does: **build → up → ngrok + cloudflare tunnels → telegram webhook registration → print all public links**.

---

## Project structure

```
/
├── docker-compose.yml          ← all 5 services + named volumes (pg_data, redis_data)
├── Makefile                    ← all dev commands
├── .env.example                ← env template (commit this)
├── .env                        ← secrets (never commit, gitignored)
├── CLAUDE.md                   ← AI assistant context (gitignored — local only)
├── docs/
│   ├── USER_DOC.md
│   ├── DEV_DOC.md
│   ├── ROADMAP.md              ← phases, tech debt
│   ├── DECISIONS.md            ← open questions and architecture ADRs
│   ├── DEPLOYMENT.md           ← full local deployment + API key setup
│   └── DEMO_REFERENCES.md      ← demo script, pitch, AI usage breakdown
├── tests/
│   ├── test_health.py          ← integration health tests
│   └── test_agent.py           ← agent integration tests
├── scripts/
│   ├── seed_demo.py            ← seeds realistic demo data
│   └── print_links.py          ← prints current public demo links (make links)
└── backend/
    ├── Dockerfile
    ├── requirements.txt        ← core dependencies
    ├── requirements-ml.txt     ← heavy ML deps (torch, whisper) — not used
    └── app/
        ├── main.py             ← FastAPI app (port 8000)
        ├── channels_main.py    ← Channels app (port 8001)
        ├── models.py           ← SQLAlchemy ORM (Customer, User, Ticket, Message)
        ├── schemas.py          ← Pydantic schemas
        ├── core/
        │   ├── config.py       ← pydantic-settings
        │   ├── logger.py       ← get_logger(__name__)
        │   ├── database.py     ← async engine, get_db()
        │   └── redis.py        ← session read/write (get_session/save_session)
        ├── agent/
        │   ├── core.py         ← LangGraph agent, run_agent()
        │   ├── identity.py     ← resolve_user(): phone-based Customer linking
        │   ├── briefing.py     ← GPT-4o-mini cross-channel agent briefing
        │   ├── sentiment.py    ← GPT-4o-mini sentiment classifier
        │   ├── prosody.py      ← voice tone heuristic (RMS + pitch via ffmpeg/numpy)
        │   └── tools.py        ← create_ticket, get_ticket_status
        ├── api/
        │   └── message.py      ← POST /api/message, GET /api/session/{id}
        ├── channels/
        │   ├── base.py                  ← abstract BaseChannel
        │   ├── telegram/adapter.py      ← ✅ incl. /start phone-share onboarding
        │   ├── webchat/adapter.py       ← ✅ WebSocket, reads ?phone= query param
        │   ├── voice/adapter.py         ← ✅ Whisper STT + OpenAI TTS
        │   └── whatsapp/adapter.py      ← ✅ Twilio WhatsApp Sandbox (TwiML reply)
        └── dashboard/
            └── metrics.py      ← /api/metrics, /api/copilot, /api/customers,
                                   /api/customers/{id}/briefing, PATCH /api/tickets/{id}
```

---

## Services and ports

| Service | Command in container | Port | Reload |
|---------|---------------------|------|--------|
| backend | `uvicorn app.main:app --reload` | 8000 | ✅ Hot reload |
| channels | `uvicorn app.channels_main:app --reload` | 8001 | ✅ Hot reload |
| frontend | `npm run dev --host` | 3000 | ✅ HMR |
| db | postgres:15-alpine | 5432 | — |
| redis | redis:7-alpine | 6379 | — |

Backend and channels share the same Docker image (`./backend`). The difference is which `main.py` is run.

---

## Message flow

```
User (Telegram / WhatsApp / WebChat / Voice)
    │
    ▼
Channel Adapter (channels service, port 8001 — Telegram/WhatsApp/Voice)
    │  parse_incoming() → IncomingMessage (+ phone, when known)
    │  POST http://backend:8000/api/message
    ▼
Backend (port 8000) — run_agent()
    │
    ├─ Load session history (Redis key: session:{session_id})
    ├─ Reconstruct LangChain messages
    ├─ LangGraph: LLM (gpt-4o) → [tools?] → LLM
    │      Tools: create_ticket(), get_ticket_status()
    ├─ classify_sentiment(user_text) → GPT-4o-mini
    ├─ Save messages to Redis (last 20, TTL 1h, AOF-persisted)
    ├─ resolve_user() → find-or-create User; if `phone` is set,
    │      find-or-create Customer(phone) and link user.customer_id
    ├─ Save both turns to Postgres (user_id set, sentiment attached;
    │      voice_tone attached for the voice channel)
    └─ Return AgentResponse
    │
Channel Adapter
    │  send_response() → user sees reply
```

**WebChat** connects directly via WebSocket (`/ws/{session_id}?phone=...`) and calls `run_agent()` in-process. The `phone` query param (set once via the "phone gate" on first load) is attached to every `IncomingMessage` for that connection.

**Voice** flow: browser mic → WebM blob → `POST /voice/message` (with `session_id` + optional `phone`) → Whisper STT *and* `agent/prosody.py::analyze_prosody()` run concurrently (`asyncio.gather`) → `run_agent()` (with `voice_tone` attached) → OpenAI TTS → MP3 base64 → browser plays audio.

**WhatsApp** flow: Twilio Sandbox POSTs `From`/`Body` (form-encoded) to `POST /whatsapp/webhook` → optional `X-Twilio-Signature` check → `run_agent()` → reply returned synchronously as TwiML (`MessagingResponse`), no outbound Twilio API call needed. `phone` is always set (it's the `From` address itself).

**Telegram** flow: on `/start`, the bot sends a one-tap "📱 Share phone number" button (`request_contact`); the resulting `Contact.phone_number` is forwarded as a normal agent turn with `phone` set, linking this Telegram user to the same `Customer` as other channels.

---

## Customer identity & agent briefing

- **`agent/identity.py::resolve_user()`** — called on every message. Finds-or-creates a `User` row keyed by `(channel, channel_user_id)` (the part of `session_id` after the first `_`). If `phone` is known and the user isn't linked yet, finds-or-creates a `Customer(phone=...)` and sets `user.customer_id`. This is the single mechanism that makes "same phone number across channels = same customer" work.
- **`agent/briefing.py::generate_briefing()`** — given a customer's full cross-channel message history (oldest first), asks GPT-4o-mini (JSON mode) for `{summary, urgency: low|medium|high, recommended_action}`. Used by `GET /api/customers/{id}/briefing` to power the Customer 360 panel. Voice messages with a `voice_tone` are tagged in the transcript (e.g. `[voice, tone: agitated]`) — an "agitated" tone nudges urgency up even if the wording is neutral. Falls back to a safe default (`urgency: medium`) on any error, same defensive pattern as `classify_sentiment`.
- **`agent/prosody.py::analyze_prosody()`** — voice channel only. Decodes the raw recording to 16kHz mono PCM via `ffmpeg`, then computes RMS loudness and an autocorrelation-based F0 pitch estimate (80-400 Hz) with `numpy`, classifying a coarse `tone: agitated | calm | flat`. A heuristic, not a trained model — see `docs/DECISIONS.md`. Stored on `Message.voice_tone`; returns `None` on any decode/analysis error (defensive pattern).

---

## Data storage

### Redis — session context (fast, temporary)

```
Key:   session:{session_id}
Value: JSON list of {role, text} dicts
TTL:   3600 seconds (1 hour)
Max:   20 messages per session (older messages trimmed)
```

```bash
# View all sessions
docker exec moei-redis-1 redis-cli KEYS "session:*"

# View a specific session
docker exec moei-redis-1 redis-cli GET "session:telegram_12345"
```

### Postgres — persistent data

Tables: `customers`, `users`, `tickets`, `messages`

- `customers` — universal cross-channel identity, keyed by `phone` (unique)
- `users` — one row per `(channel, channel_user_id)`, optionally linked to a `customer` via `customer_id`
- `messages` — has both `session_id` (channel-local) and `user_id` (set via `resolve_user()`), enabling cross-channel history joins. `voice_tone` (nullable) holds the prosody-based tone label (`agitated | calm | flat`) for voice-channel user messages — see `agent/prosody.py`

```bash
# Connect
docker exec -it moei-db-1 psql -U moei -d moei

# Useful queries
\dt                                                  -- list tables
SELECT session_id, channel, role, sentiment, voice_tone, LEFT(text, 60) FROM messages ORDER BY timestamp DESC LIMIT 20;
SELECT * FROM tickets ORDER BY created_at DESC;

-- Cross-channel history for one customer
SELECT m.channel, m.role, LEFT(m.text, 60), m.timestamp
FROM messages m
JOIN users u ON u.id = m.user_id
JOIN customers c ON c.id = u.customer_id
WHERE c.phone = '+9715xxxxxxxx'
ORDER BY m.timestamp;
```

**Volume:** `pg_data` (Docker named volume). Survives `make down`. Destroyed by `make fclean`.

---

## Environment variables reference

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `PUBLIC_BASE_URL` | — | auto | Public web app URL, set by `make ngrok` |
| `POSTGRES_HOST` | `db` | — | DB hostname (use `db` in Docker) |
| `POSTGRES_PORT` | `5432` | — | DB port |
| `POSTGRES_DB` | `moei` | — | Database name |
| `POSTGRES_USER` | `moei` | — | DB user |
| `POSTGRES_PASSWORD` | `changeme` | ✅ | DB password |
| `REDIS_HOST` | `redis` | — | Redis hostname |
| `REDIS_PORT` | `6379` | — | Redis port |
| `OPENAI_API_KEY` | — | ✅ | Powers everything: GPT-4o (agent), GPT-4o-mini (sentiment + briefing), Whisper (STT), TTS |
| `NGROK_AUTH_TOKEN` | — | for `make ngrok` | ngrok authtoken (`ngrok config add-authtoken ...`) |
| `TELEGRAM_BOT_TOKEN` | — | ✅ | From @BotFather |
| `TELEGRAM_WEBHOOK_URL` | — | auto | Set by `make cloudflare` |
| `TWILIO_AUTH_TOKEN` | `""` | optional | Enables `X-Twilio-Signature` verification on `/whatsapp/webhook`; leave empty for sandbox demos |
| `BACKEND_URL` | `http://backend:8000` | — | Inter-service URL (channels → backend) |
| `ELEVENLABS_API_KEY` | — | unused | Reserved for a future TTS upgrade |
| `APP_ENV` | `development` | — | Controls SQLAlchemy echo |
| `LOG_LEVEL` | `INFO` | — | `DEBUG`, `INFO`, `WARNING`, `ERROR` |

> **Note:** `OPENAI_MODEL` and `TTS_VOICE` appear in some older `.env` files but are not read by `app.core.config.Settings` — models are currently hardcoded (`gpt-4o` for the agent, `gpt-4o-mini` for sentiment/briefing, `tts-1` / `nova` for TTS in `voice/adapter.py`). Safe to leave unset.

---

## Adding a new channel

Every channel lives in `backend/app/channels/{name}/adapter.py` and must implement `BaseChannel`:

```python
from app.channels.base import BaseChannel
from app.schemas import IncomingMessage, AgentResponse

class MyChannel(BaseChannel):
    async def parse_incoming(self, raw: dict) -> IncomingMessage | None:
        # Parse raw webhook payload → IncomingMessage
        # Return None to silently skip (e.g. non-message events)
        ...

    async def send_response(self, response: AgentResponse, raw: dict) -> None:
        # Deliver reply to the user on this channel
        ...
```

Then register the router in `channels_main.py`:

```python
from app.channels.myname.adapter import router as myname_router
app.include_router(myname_router)
```

Session ID convention: `{channel_name}_{platform_user_id}` (e.g. `telegram_12345`).

---

## Coding conventions

1. **First line of every file** = full path as a comment: `# /backend/app/core/logger.py`
2. **All comments in English**
3. **No hardcoded values** — all config via `app.core.config.settings`
4. **Every module** uses: `from app.core.logger import get_logger` / `logger = get_logger(__name__)`
5. **Log:** incoming messages, agent responses, all errors
6. **Before merging to main:** `/health` green + all tests passing

---

## API reference

Interactive docs available at **http://localhost:8000/docs** (Swagger UI).

| Endpoint | Method | Service | Description |
|----------|--------|---------|-------------|
| `/health` | GET | backend | `{backend, redis, db}` status |
| `/health` | GET | channels | `{channels}` status |
| `/api/message` | POST | backend | Run agent: IncomingMessage → AgentResponse |
| `/api/session/{id}` | GET | backend | Fetch Redis session history |
| `/api/metrics` | GET | backend | Dashboard metrics (sessions, tickets, sentiment, channels) |
| `/api/copilot` | GET | backend | Recent conversations + AI-suggested replies for human agents |
| `/api/customers` | GET | backend | Customers with ≥1 message, sorted by last activity |
| `/api/customers/{id}/briefing` | GET | backend | Cross-channel history + tickets + AI briefing for one customer |
| `/api/tickets/{id}` | PATCH | backend | Update ticket status (`open`/`in_progress`/`resolved`/`escalated`) |
| `/ws/{session_id}` | WS | backend | WebChat WebSocket (`?phone=` optional query param) |
| `/telegram/webhook` | POST | channels | Telegram update receiver |
| `/telegram/setup` | POST | channels | Register webhook with Telegram |
| `/voice/message` | POST | channels | Voice: audio file → STT → agent → TTS audio response |
| `/whatsapp/webhook` | POST | channels | Twilio WhatsApp Sandbox webhook (TwiML reply) |

---

## Running tests

```bash
# Run all tests (from project root)
make test

# Equivalent manual command
docker compose exec \
  -e TEST_BACKEND_URL=http://backend:8000 \
  -e TEST_CHANNELS_URL=http://channels:8001 \
  -e TEST_FRONTEND_URL=http://frontend:3000 \
  backend python -m pytest /tests/ -v
```

Tests live in `tests/` at project root, mounted into the backend container at `/tests`.  
Tests call real running services — requires `make up` first.

---

## Seeding demo data

```bash
make seed
```

Runs `scripts/seed_demo.py` — sends 8 realistic conversations (English + Arabic, webchat + telegram) through the live backend. Uses real GPT-4o. Costs ~$0.10.  
Run once before the demo to populate the dashboard with meaningful data.

---

## Database schema changes

Tables are auto-created on startup via `Base.metadata.create_all()`.  
For schema changes during development: `make fclean && make bup` (drops and recreates all tables).

Alembic is included in `requirements.txt` for future migration management — not yet configured.

---

## Troubleshooting

**Container won't start:**
```bash
make logs-backend     # check Python errors
make logs-channels    # check channel service errors
```

**Telegram webhook not receiving messages:**
```bash
make telegram-setup   # re-register webhook
# Check ngrok is running: curl http://localhost:4040/api/tunnels
```

**WhatsApp (Twilio Sandbox) not replying:**
Tunnel URLs change on every `make bup` — Twilio has no setup API like Telegram, so the Sandbox "when a message comes in" webhook URL must be re-pasted manually in the Twilio console after each restart. Run `make links` to get the current `/whatsapp/webhook` URL. See [DEPLOYMENT.md](DEPLOYMENT.md).

**`No module named 'app'`:**  
Backend volume mount works because the working directory is `/app` and `./backend` is mounted there. If running locally (outside Docker), set `PYTHONPATH=backend`.

**Redis connection error:**  
```bash
docker exec moei-redis-1 redis-cli ping  # should return PONG
```

**Postgres connection error:**  
```bash
docker exec moei-db-1 pg_isready -U moei -d moei
```

**Voice: no audio in browser:**  
Browser requires HTTPS or localhost for microphone access. Works on `localhost:3000`.
