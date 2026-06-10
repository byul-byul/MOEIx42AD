# User Documentation — MOEI AI Customer Engagement Agent

This guide is for **end users, customer service operators, and administrators** who interact with or manage the MOEI AI agent platform.

---

## What services does this platform provide?

The platform delivers a unified AI customer service agent for MOEI (Ministry of Energy and Infrastructure, Abu Dhabi). Customers can reach the agent through multiple channels, all sharing the same agent, ticket store, and — when a phone number is known — the same cross-channel customer profile:

| Channel | How to access |
|---------|--------------|
| **Telegram** | Search [@personal_ai_assistant_2025_bot](https://t.me/personal_ai_assistant_2025_bot) and send a message |
| **WhatsApp** | Message the Twilio Sandbox number from your phone (see [DEPLOYMENT.md](DEPLOYMENT.md) for the join code) |
| **Web Chat** | Open [http://localhost:3000](http://localhost:3000) in a browser |
| **Voice (browser mic)** | In Web Chat, tap 🎤, speak, and the agent replies with audio |
| **Dashboard** | Open [http://localhost:3000/dashboard](http://localhost:3000/dashboard) (operators only) |

The agent understands and responds in **English and Arabic**. It automatically detects the language from the customer's message.

To get the current public links for a running deployment (web app, dashboard, Telegram bot, WhatsApp webhook), run `make links`.

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
1. Builds all Docker images
2. Starts all services (Postgres, Redis, backend, channels, frontend)
3. Starts an ngrok tunnel (public web app URL) and a Cloudflare tunnel (Telegram/WhatsApp webhooks)
4. Registers the Telegram webhook automatically
5. Prints all current public links (web app, dashboard, Telegram bot, WhatsApp webhook) — same as running `make links`

First start takes 2–3 minutes (downloading images). Subsequent starts are under 30 seconds.

**Note:** tunnel URLs change on every `make bup`. The WhatsApp webhook URL must be re-registered manually in the Twilio Sandbox console after each restart — see [DEPLOYMENT.md](DEPLOYMENT.md).

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
2. **Phone gate:** on first visit, enter a phone number (e.g. `+9715xxxxxxxx`). This is your **cross-channel customer identity** — the same number used on WhatsApp or shared with the Telegram bot links your conversations together. The number is stored in the browser (`localStorage`) so you only enter it once.
3. Type your message and press **Enter** (or click **Send**)
4. The agent responds in a few seconds
5. Your conversation is saved — if you close and reopen the page, history is restored
6. Click **New Chat** in the top-right corner to start a fresh session — this resets the session ID but keeps your phone number, so the customer profile stays linked

The small text below "Customer Support" shows your **session ID** — useful for the demo to show cross-channel context.

---

## Using Telegram

1. Open the bot link and send `/start`
2. The bot greets you and shows a **"📱 Share phone number"** button (one tap, no typing)
3. Tapping it links this Telegram account to the same cross-channel customer profile as WhatsApp/web chat
4. From then on, just chat normally — the agent replies in English or Arabic depending on your message

---

## Using WhatsApp

1. Join the Twilio Sandbox once (see [DEPLOYMENT.md](DEPLOYMENT.md) for the exact join code/number — this is a one-time step per phone number)
2. Send any message — the agent replies in the same chat
3. Your WhatsApp number is automatically your cross-channel customer identity (no phone gate needed — Twilio provides it on every message)

---

## Operations Dashboard

Open [http://localhost:3000/dashboard](http://localhost:3000/dashboard).

The dashboard refreshes every **5 seconds** and shows:

### Sentiment alert banner

If any recent customer message was classified as **negative** sentiment, a red banner appears at the top of the page listing the channel, session, and message preview. If the customer is identified (has a linked phone number), a **"View Customer"** button jumps straight to their briefing in Customer 360 below.

### KPI cards

| Card | What it means |
|------|--------------|
| **Active Sessions** | Customers currently in conversation (Redis keys) |
| **Total Tickets** | All support tickets ever created |
| **Open Tickets** | Tickets waiting for resolution |
| **Escalated** | Cases flagged as urgent or safety-critical |

### Charts

- **Messages by channel** — how many user messages came from each channel
- **Tickets by status** — distribution of open / in progress / resolved / escalated tickets
- **Customer Sentiment** — distribution of positive / neutral / negative across recent messages

### AI Co-pilot — Suggested Replies

Live feed of the 10 most recent customer messages, each with the channel, sentiment, and the AI-generated reply that was actually sent — giving a human agent a ready-made response to reuse or adapt.

### Recent Tickets

Table of the last 10 tickets with channel, status, escalation flag, and creation time.

### Customer 360

A two-column panel at the bottom of the dashboard:

- **Left — customer list:** every customer with at least one linked message, showing phone number, channel badges (Telegram/WhatsApp/Voice/Web), last message preview, and last sentiment emoji. Click a customer to select them.
- **Right — briefing panel:** for the selected customer —
  - **Urgency badge** (low / medium / high) and an **AI-generated summary** of their situation, produced by GPT-4o-mini from their full cross-channel history
  - **Recommended action** — one concrete next step for the agent
  - **Tickets** with one-click action buttons: **In Progress / Resolve / Escalate**
  - **Conversation timeline** — every message across every channel, oldest first, with channel and role labels

This is the "unified omnichannel" view: a customer who messaged on Telegram, then WhatsApp, then web chat (using the same phone number) shows up as **one** customer with one merged history.

---

## Credentials and secrets

All credentials are stored in the `.env` file at the project root. **Never commit this file.**

The `.env.example` file lists all required variables — copy it to `.env` and fill in your values:

| Variable | Description |
|----------|-------------|
| `OPENAI_API_KEY` | OpenAI API key — powers the agent (GPT-4o), sentiment/briefing (GPT-4o-mini), voice STT (Whisper) and TTS (required) |
| `TELEGRAM_BOT_TOKEN` | Obtained from @BotFather in Telegram (required) |
| `POSTGRES_PASSWORD` | Database password (choose a strong password) |
| `NGROK_AUTH_TOKEN` | ngrok authtoken, used by `make ngrok` for the public web app tunnel |
| `TWILIO_AUTH_TOKEN` | Optional — enables `X-Twilio-Signature` verification on the WhatsApp webhook |

For where to get each of these and the full step-by-step setup, see [DEPLOYMENT.md](DEPLOYMENT.md).

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
