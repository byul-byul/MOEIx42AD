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

`make bup` does: **ngrok → build → up → telegram webhook registration**.

---

## Project structure

```
/
├── docker-compose.yml          ← all 5 services
├── Makefile                    ← all dev commands
├── .env.example                ← env template (commit this)
├── .env                        ← secrets (never commit, gitignored)
├── CLAUDE.md                   ← AI assistant context (gitignored — local only)
├── docs/
│   ├── USER_DOC.md
│   ├── DEV_DOC.md
│   ├── ROADMAP.md
│   └── DECISIONS.md            ← open questions and architecture ADRs
├── tests/
│   ├── test_health.py          ← 5 integration health tests
│   └── test_agent.py           ← 5 agent integration tests
├── scripts/
│   └── seed_demo.py            ← seeds realistic demo data
└── backend/
    ├── Dockerfile
    ├── requirements.txt        ← core dependencies
    ├── requirements-ml.txt     ← heavy ML deps (torch, whisper) — not used
    └── app/
        ├── main.py             ← FastAPI app (port 8000)
        ├── channels_main.py    ← Channels app (port 8001)
        ├── models.py           ← SQLAlchemy ORM
        ├── schemas.py          ← Pydantic schemas
        ├── core/
        │   ├── config.py       ← pydantic-settings
        │   ├── logger.py       ← get_logger(__name__)
        │   ├── database.py     ← async engine, get_db()
        │   └── redis.py        ← session read/write
        ├── agent/
        │   ├── core.py         ← LangGraph agent, run_agent()
        │   ├── memory.py       ← Redis session helpers
        │   ├── sentiment.py    ← GPT-4o-mini sentiment classifier
        │   └── tools.py        ← create_ticket, get_ticket_status
        ├── api/
        │   └── message.py      ← POST /api/message, GET /api/session/{id}
        ├── channels/
        │   ├── base.py                  ← abstract BaseChannel
        │   ├── telegram/adapter.py      ← ✅ implemented
        │   ├── webchat/adapter.py       ← ✅ implemented (WebSocket)
        │   ├── voice/adapter.py         ← ✅ implemented (Whisper STT + OpenAI TTS)
        │   └── whatsapp/adapter.py      ← ⬜ Phase 5 stub
        └── dashboard/
            └── metrics.py      ← GET /api/metrics, GET /api/copilot
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
User (Telegram / WebChat / Voice)
    │
    ▼
Channel Adapter (channels service, port 8001)
    │  parse_incoming() → IncomingMessage
    │  POST http://backend:8000/api/message
    ▼
Backend (port 8000) — run_agent()
    │
    ├─ Load session history (Redis key: session:{session_id})
    ├─ Reconstruct LangChain messages
    ├─ LangGraph: LLM → [tools?] → LLM
    │      Tools: create_ticket(), get_ticket_status()
    ├─ classify_sentiment(user_text) → GPT-4o-mini
    ├─ Save messages to Redis (last 20, TTL 1h)
    ├─ Save messages to Postgres (permanent, with sentiment)
    └─ Return AgentResponse
    │
Channel Adapter
    │  send_response() → user sees reply
```

**WebChat** connects directly via WebSocket (`/ws/{session_id}`) and calls `run_agent()` in-process.

**Voice** flow: browser mic → WebM blob → `POST /voice/message` → Whisper STT → `run_agent()` → OpenAI TTS → MP3 base64 → browser plays audio.

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

Tables: `users`, `tickets`, `messages`

```bash
# Connect
docker exec -it moei-db-1 psql -U moei -d moei

# Useful queries
\dt                                                  -- list tables
SELECT session_id, channel, role, sentiment, LEFT(text, 60) FROM messages ORDER BY timestamp DESC LIMIT 20;
SELECT * FROM tickets ORDER BY created_at DESC;
```

**Volume:** `pg_data` (Docker named volume). Survives `make down`. Destroyed by `make fclean`.

---

## Environment variables reference

| Variable | Default | Required | Description |
|----------|---------|----------|-------------|
| `POSTGRES_HOST` | `db` | — | DB hostname (use `db` in Docker) |
| `POSTGRES_PORT` | `5432` | — | DB port |
| `POSTGRES_DB` | `moei` | — | Database name |
| `POSTGRES_USER` | `moei` | — | DB user |
| `POSTGRES_PASSWORD` | `changeme` | ✅ | DB password |
| `REDIS_HOST` | `redis` | — | Redis hostname |
| `REDIS_PORT` | `6379` | — | Redis port |
| `OPENAI_API_KEY` | — | ✅ | GPT-4o + GPT-4o-mini + Whisper + TTS |
| `TELEGRAM_BOT_TOKEN` | — | ✅ | From @BotFather |
| `TELEGRAM_WEBHOOK_URL` | — | auto | Set by `make ngrok` |
| `BACKEND_URL` | `http://backend:8000` | — | Inter-service URL (channels → backend) |
| `TTS_VOICE` | `nova` | — | OpenAI TTS voice (alloy/echo/fable/onyx/nova/shimmer) |
| `WHATSAPP_TOKEN` | — | Phase 5 | Meta Cloud API token |
| `WHATSAPP_PHONE_NUMBER_ID` | — | Phase 5 | Meta phone number ID |
| `WHATSAPP_VERIFY_TOKEN` | — | Phase 5 | Webhook verify token |
| `ELEVENLABS_API_KEY` | — | unused | Kept for future TTS upgrade |
| `APP_ENV` | `development` | — | Controls SQLAlchemy echo |
| `LOG_LEVEL` | `INFO` | — | `DEBUG`, `INFO`, `WARNING`, `ERROR` |

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
| `/ws/{session_id}` | WS | backend | WebChat WebSocket |
| `/telegram/webhook` | POST | channels | Telegram update receiver |
| `/telegram/setup` | POST | channels | Register webhook with Telegram |
| `/voice/message` | POST | channels | Voice: audio file → STT → agent → TTS audio response |

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
