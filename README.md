# MOEI AI Customer Engagement Agent

Omnichannel AI customer service agent for the Ministry of Energy and Infrastructure (MOEI), Abu Dhabi.  
Built for the **MOEI AD42 Agentic AI Hackathon** — 48 hours, June 9–11 2026.

---

## What it does

A unified AI agent that handles customer inquiries across multiple channels with **one shared customer identity**:

| Channel | Status |
|---------|--------|
| Telegram | ✅ Live |
| WhatsApp (Twilio Sandbox) | ✅ Live |
| Web Chat | ✅ Live |
| Voice (browser mic) | ✅ Live |

- Responds in **English and Arabic** (auto-detected)
- Creates and tracks **support tickets** in Postgres
- Maintains **session memory** in Redis (1h TTL, AOF-persisted, last 20 messages)
- **Unified cross-channel customer identity** — phone number links a customer's Telegram, WhatsApp, web chat, and voice conversations into one profile (`customers` table)
- Classifies **sentiment** per message (positive / neutral / negative) via GPT-4o-mini
- Escalates **safety-critical issues** automatically (gas leaks, electrical hazards)
- Real-time **leadership dashboard**: live metrics, sentiment chart, ticket table, **negative-sentiment alert banner**
- **AI co-pilot panel** — live feed of conversations with AI-suggested replies for human agents
- **Customer 360 / AI case briefing** — for any customer, an AI-generated summary of their full cross-channel history, an urgency score, a recommended action, and one-click ticket actions (In Progress / Resolve / Escalate)

---

## Quick start

```bash
# 1. Clone and configure
cp .env.example .env
# Fill in: OPENAI_API_KEY, TELEGRAM_BOT_TOKEN, POSTGRES_PASSWORD
# (full instructions + where to get every key/token: docs/DEPLOYMENT.md)

# 2. Start everything (build + up + ngrok/cloudflare tunnels + telegram webhook + print links)
make bup

# 3. Open
# Web Chat:   http://localhost:3000
# Dashboard:  http://localhost:3000/dashboard
# API Docs:   http://localhost:8000/docs

# 4. Seed realistic demo data (optional but recommended)
make seed
```

For a brand-new machine — including where to register for `OPENAI_API_KEY`,
`TELEGRAM_BOT_TOKEN`, `NGROK_AUTH_TOKEN`, `TWILIO_AUTH_TOKEN`, and how to join
the WhatsApp Sandbox — see **[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)**.

---

## Architecture

```
┌─────────────┐     ┌──────────────────────────────────────┐
│  Telegram   │────▶│  Channels Service (port 8001)        │
│  WhatsApp   │     │  Dumb adapters: parse → forward      │
│  Voice      │     │  (each captures phone → identity)    │
└─────────────┘     └────────────────┬─────────────────────┘
                                     │ POST /api/message (+ phone)
                                     ▼
┌─────────────┐     ┌──────────────────────────────────────┐
│  Web Chat   │────▶│  Backend Service (port 8000)         │
│  WebSocket  │     │  LangGraph + GPT-4o agent            │
└─────────────┘     │  + sentiment (GPT-4o-mini)           │
                    │  + AI briefing (GPT-4o-mini)          │
                    │  POST /api/message                   │
                    │  GET  /api/metrics                   │
                    │  GET  /api/copilot                   │
                    │  GET  /api/customers                 │
                    │  GET  /api/customers/{id}/briefing   │
                    │  PATCH /api/tickets/{id}             │
                    │  GET  /api/session/{id}              │
                    │  WS   /ws/{session_id}               │
                    └──────────┬──────────────┬────────────┘
                               │              │
                    ┌──────────▼──┐  ┌────────▼──────────┐
                    │  Postgres   │  │  Redis            │
                    │  customers, │  │  sessions, TTL 1h │
                    │  users,     │  │  AOF-persisted    │
                    │  tickets,   │  │                   │
                    │  messages   │  │                   │
                    └─────────────┘  └───────────────────┘
                               │
                    ┌──────────▼──────────────────────────┐
                    │  Frontend (port 3000)                │
                    │  React + Recharts                    │
                    │  Web chat + voice | Dashboard:       │
                    │  KPIs, sentiment alerts, co-pilot,   │
                    │  Customer 360 (cross-channel briefing)│
                    └───────────────────────────────────────┘
```

**Rule:** Agent is channel-agnostic. Channels are dumb adapters. Never mix them.

---

## Services

| Service | Tech | Port |
|---------|------|------|
| backend | FastAPI + asyncpg + LangGraph | 8000 |
| channels | FastAPI (Telegram, WhatsApp, Voice) | 8001 |
| frontend | React + Vite + Recharts | 3000 |
| db | Postgres 15 | 5432 |
| redis | Redis 7 (AOF persistence) | 6379 |

---

## Makefile commands

| Command | Description |
|---------|-------------|
| `make bup` | Full start: build → up → ngrok + cloudflare tunnels → register Telegram webhook → print all public links |
| `make up` | Start all containers (detached) |
| `make down` | Stop containers |
| `make build` | Build Docker images |
| `make ps` | Status + health check of all services |
| `make logs` | Follow all logs |
| `make logs-backend` | Follow backend logs only |
| `make logs-channels` | Follow channels logs only |
| `make logs-frontend` | Follow frontend logs only |
| `make ngrok` | Start ngrok tunnel (web app), write URL to .env |
| `make cloudflare` | Start cloudflared tunnel (Telegram/WhatsApp webhooks), write URL to .env |
| `make telegram-setup` | Register Telegram webhook (once after deploy) |
| `make links` | Print current public links (web app, dashboard, Telegram bot, WhatsApp webhook) |
| `make test` | Run integration tests (requires services up) |
| `make seed` | Seed realistic demo conversations into DB |
| `make clean` | Remove caches and orphaned containers |
| `make fclean` | clean + remove volumes (deletes all data) |

**Note:** the WhatsApp Sandbox webhook URL must be re-registered manually in
the Twilio console after every `make bup` (no setup API like Telegram's) —
see [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).

---

## Environment variables

See [`.env.example`](.env.example) for the full list.
Required before first run: `OPENAI_API_KEY`, `TELEGRAM_BOT_TOKEN`, `POSTGRES_PASSWORD`.
For where to get every key/token (OpenAI, Telegram BotFather, ngrok,
Twilio WhatsApp Sandbox) and full setup steps, see
[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).

---

## Documentation

| File | Description |
|------|-------------|
| [`docs/USER_DOC.md`](docs/USER_DOC.md) | End-user and operator guide — using each channel, the dashboard, Customer 360 |
| [`docs/DEV_DOC.md`](docs/DEV_DOC.md) | Developer setup, architecture, message flow, API reference |
| [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) | Full local deployment guide — `.env` setup, where to get every API key/token, tunnels, troubleshooting |
| [`docs/DEMO_REFERENCES.md`](docs/DEMO_REFERENCES.md) | Demo script, pitch material, AI usage breakdown, problem statement, value proposition, why we should win |
| [`docs/ROADMAP.md`](docs/ROADMAP.md) | Phases, tech debt, future work |
| [`docs/DECISIONS.md`](docs/DECISIONS.md) | Open questions and architecture decisions |

---

## Demo scenario (3 minutes)

1. Customer writes in Telegram in Arabic, shares phone number → agent replies in Arabic, opens a ticket
2. Same customer messages WhatsApp (same phone number) — frustrated tone
3. Dashboard shows a **negative sentiment alert** → "View Customer" opens **Customer 360**: merged Telegram + WhatsApp history, AI summary, urgency, recommended action
4. One-click **Escalate** on the ticket — dashboard KPIs update live
5. Customer clicks 🎤 mic in web chat → agent hears question, replies with audio
6. Leadership view: live metrics, sentiment trend, channel/ticket charts

Full script with talking points: [docs/DEMO_REFERENCES.md](docs/DEMO_REFERENCES.md).
Run `make seed` before the demo to populate realistic multi-channel data.
