# MOEI AI Customer Engagement Agent

Omnichannel AI customer service agent for the Ministry of Energy and Infrastructure (MOEI), Abu Dhabi.  
Built for the **MOEI AD42 Agentic AI Hackathon** — 48 hours, June 9–11 2026.

---

## What it does

A unified AI agent that handles customer inquiries across multiple channels with shared context:

| Channel | Status | Port |
|---------|--------|------|
| Telegram | ✅ Live | — (webhook) |
| Web Chat | ✅ Live | 3000 |
| Voice | 🔄 Phase 4 | — |
| WhatsApp | ⬜ Phase 5 | — |

- Responds in **English and Arabic** (auto-detected)
- Creates and tracks **support tickets** in Postgres
- Maintains **session memory** in Redis (1h TTL, last 20 messages)
- Persists all **messages to DB** for audit and analytics
- Escalates **safety-critical issues** automatically
- Real-time **leadership dashboard** with live metrics

---

## Quick start

```bash
# 1. Clone and configure
cp .env.example .env
# Fill in: OPENAI_API_KEY, TELEGRAM_BOT_TOKEN, POSTGRES_PASSWORD

# 2. Start everything (ngrok + build + up + telegram webhook)
make bup

# 3. Open
# Web Chat:   http://localhost:3000
# Dashboard:  http://localhost:3000/dashboard
# API Docs:   http://localhost:8000/docs
```

---

## Architecture

```
┌─────────────┐     ┌──────────────────────────────────────┐
│  Telegram   │────▶│  Channels Service (port 8001)        │
│  WhatsApp   │     │  Dumb adapters: parse → forward      │
│  Voice      │     └────────────────┬─────────────────────┘
└─────────────┘                      │ POST /api/message
                                     ▼
┌─────────────┐     ┌──────────────────────────────────────┐
│  Web Chat   │────▶│  Backend Service (port 8000)         │
│  WebSocket  │     │  LangGraph + GPT-4o agent            │
└─────────────┘     │  POST /api/message                   │
                    │  GET  /api/metrics                   │
                    │  GET  /api/session/{id}              │
                    │  WS   /ws/{session_id}               │
                    └──────────┬──────────────┬────────────┘
                               │              │
                    ┌──────────▼──┐  ┌────────▼──────────┐
                    │  Postgres   │  │  Redis            │
                    │  (persist)  │  │  (sessions, TTL)  │
                    └─────────────┘  └───────────────────┘
                               │
                    ┌──────────▼──────────┐
                    │  Frontend (port 3000)│
                    │  React + Recharts   │
                    └─────────────────────┘
```

**Rule:** Agent is channel-agnostic. Channels are dumb adapters. Never mix them.

---

## Services

| Service | Tech | Port |
|---------|------|------|
| backend | FastAPI + asyncpg + LangGraph | 8000 |
| channels | FastAPI (Telegram, Voice, WhatsApp) | 8001 |
| frontend | React + Vite + Recharts | 3000 |
| db | Postgres 15 | 5432 |
| redis | Redis 7 | 6379 |

---

## Makefile commands

| Command | Description |
|---------|-------------|
| `make bup` | Full start: ngrok → build → up → register Telegram webhook |
| `make up` | Start all containers (detached) |
| `make down` | Stop containers |
| `make build` | Build Docker images |
| `make ps` | Status + health check of all services |
| `make logs` | Follow all logs |
| `make logs-backend` | Follow backend logs only |
| `make logs-channels` | Follow channels logs only |
| `make logs-frontend` | Follow frontend logs only |
| `make ngrok` | Start ngrok tunnel, write URL to .env |
| `make telegram-setup` | Register Telegram webhook (once after deploy) |
| `make clean` | Remove containers + Python cache |
| `make fclean` | clean + remove volumes (deletes all data) |

---

## Environment variables

See [`.env.example`](.env.example) for the full list.  
Required before first run: `OPENAI_API_KEY`, `TELEGRAM_BOT_TOKEN`, `POSTGRES_PASSWORD`.

---

## Documentation

| File | Description |
|------|-------------|
| [`docs/USER_DOC.md`](docs/USER_DOC.md) | End-user and operator guide |
| [`docs/DEV_DOC.md`](docs/DEV_DOC.md) | Developer setup and architecture |
| [`docs/ROADMAP.md`](docs/ROADMAP.md) | Phases, tech debt, future work |
| [`CLAUDE.md`](CLAUDE.md) | AI assistant context (coding conventions, demo script) |

---

## Demo scenario (3 minutes)

1. Customer writes in Telegram in Arabic → agent replies in Arabic
2. Same customer opens web chat → context already there (shared Redis session)
3. Customer calls → agent hears and responds with voice *(Phase 4)*
4. Human agent sees AI co-pilot suggestions in real time *(Phase 6)*
5. Leadership views dashboard — live metrics + ticket trends
