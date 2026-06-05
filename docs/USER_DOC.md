# User Documentation — MOEI AI Customer Engagement Agent

This guide is for **end users, customer service operators, and administrators** who interact with or manage the MOEI AI agent platform.

---

## What services does this platform provide?

The platform delivers a unified AI customer service agent for MOEI (Ministry of Energy and Infrastructure, Abu Dhabi). Customers can reach the agent through multiple channels:

| Channel | How to access |
|---------|--------------|
| **Telegram** | Search [@personal_ai_assistant_2025_bot](https://t.me/personal_ai_assistant_2025_bot) and send a message |
| **Web Chat** | Open [http://localhost:3000](http://localhost:3000) in a browser |
| **Dashboard** | Open [http://localhost:3000/dashboard](http://localhost:3000/dashboard) (operators only) |

The agent understands and responds in **English and Arabic**. It automatically detects the language from the customer's message.

---

## What can the agent help with?

- Electricity and water service inquiries
- Bill payments and account information
- Service connection requests and outage reports
- Meter readings and technical issues
- Status check of existing support tickets
- General ministry services and procedures

For **urgent safety issues** (gas leaks, electrical hazards, fires), the agent will immediately advise contacting emergency services and flag the case for escalation.

---

## Starting and stopping the platform

### Start

```bash
make bup
```

This command:
1. Starts an ngrok tunnel for Telegram webhook
2. Builds all Docker images
3. Starts all services (Postgres, Redis, backend, channels, frontend)
4. Registers the Telegram webhook automatically

First start takes 2–3 minutes (downloading images). Subsequent starts are under 30 seconds.

### Stop

```bash
make down       # stop containers, keep data
make fclean     # stop containers AND delete all data (tickets, messages, sessions)
```

---

## Accessing the platform

| URL | What you see |
|-----|-------------|
| http://localhost:3000 | Web chat (customer-facing) |
| http://localhost:3000/dashboard | Operations dashboard (operators) |
| http://localhost:8000/docs | API documentation (developers) |

---

## Using the Web Chat

1. Open [http://localhost:3000](http://localhost:3000)
2. Type your message and press **Enter** (or click **Send**)
3. The agent responds in a few seconds
4. Your conversation is saved — if you close and reopen the page, history is restored
5. Click **New Chat** in the top-right corner to start a fresh session

The small text below "Customer Support" shows your **session ID** — useful for the demo to show cross-channel context.

---

## Operations Dashboard

Open [http://localhost:3000/dashboard](http://localhost:3000/dashboard).

The dashboard refreshes every **5 seconds** and shows:

| Card | What it means |
|------|--------------|
| **Active Sessions** | Customers currently in conversation (Redis keys) |
| **Total Tickets** | All support tickets ever created |
| **Open Tickets** | Tickets waiting for resolution |
| **Escalated** | Cases flagged as urgent or safety-critical |

Charts show:
- **Messages by channel** — how many user messages came from each channel
- **Tickets by status** — distribution of open / in progress / resolved / escalated tickets

The **Recent Tickets** table lists the last 10 tickets with channel, status, escalation flag, and creation time.

---

## Credentials and secrets

All credentials are stored in the `.env` file at the project root. **Never commit this file.**

The `.env.example` file lists all required variables — copy it to `.env` and fill in your values:

| Variable | Description |
|----------|-------------|
| `OPENAI_API_KEY` | GPT-4o API key (required for the agent to work) |
| `TELEGRAM_BOT_TOKEN` | Obtained from @BotFather in Telegram |
| `POSTGRES_PASSWORD` | Database password (choose a strong password) |
| `ELEVENLABS_API_KEY` | Text-to-speech for voice channel (Phase 4) |
| `WHATSAPP_TOKEN` | Meta Cloud API token (Phase 5) |

---

## Checking that services are running

```bash
make ps
```

Expected output:

```
NAME                STATUS          PORTS
moei-backend-1      Up (healthy)    0.0.0.0:8000->8000/tcp
moei-channels-1     Up              0.0.0.0:8001->8001/tcp
moei-db-1           Up (healthy)    0.0.0.0:5432->5432/tcp
moei-frontend-1     Up              0.0.0.0:3000->3000/tcp
moei-redis-1        Up (healthy)    0.0.0.0:6379->6379/tcp

--- backend ---
{"backend": "ok", "redis": "ok", "db": "ok"}

--- channels ---
{"channels": "ok"}

--- frontend ---
{"frontend": "200", "url": "http://localhost:3000"}
```

If any value shows `"error"` — fix it before proceeding. Check logs with `make logs-backend`.

---

## Viewing conversation data

Connect to the database directly:

```bash
docker exec -it moei-db-1 psql -U moei -d moei
```

Useful queries:

```sql
-- All messages today
SELECT session_id, channel, role, LEFT(text, 80), timestamp
FROM messages
ORDER BY timestamp DESC
LIMIT 20;

-- Open tickets
SELECT id, channel, status, escalate, created_at
FROM tickets
WHERE status = 'open';

-- Escalated cases
SELECT t.id, t.channel, t.created_at, m.text
FROM tickets t
JOIN messages m ON m.ticket_id = t.id AND m.role = 'user'
WHERE t.escalate = true;
```

---

## Telegram bot management

The Telegram bot name is configured via [@BotFather](https://t.me/BotFather):

- `/setname` — change the bot's display name
- `/setdescription` — set the bot description shown in the profile
- `/setuserpic` — set a bot avatar

The webhook is registered automatically by `make bup`. To re-register manually:

```bash
make telegram-setup
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Web chat shows "Reconnecting…" | Check `make ps` — backend may be starting up. Wait 10s and refresh. |
| Telegram bot doesn't reply | Run `make telegram-setup` to re-register the webhook |
| Dashboard shows no data | Send at least one message through any channel first |
| `make bup` fails on ngrok | Install ngrok: `brew install ngrok` and authenticate: `ngrok config add-authtoken <token>` |
| Agent replies are slow | Normal — GPT-4o takes 2–5 seconds. Check internet connection if longer. |
