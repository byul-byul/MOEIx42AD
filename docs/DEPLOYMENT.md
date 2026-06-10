# Deployment Guide — Local Setup for the MOEI AI Customer Engagement Agent

This is a step-by-step guide to get the full stack (backend, channels,
frontend, Postgres, Redis, Telegram, WhatsApp, Voice) running on a fresh
machine — including **where to get every API key/token** and **how the
public tunnels work**. If you're prepping for a demo, read this top to
bottom once, then just use the "Demo day checklist" at the end.

---

## 1. Prerequisites

| Tool | Why | Install |
|------|-----|---------|
| Docker + Docker Compose | Runs all 5 services | https://docs.docker.com/get-docker/ |
| Make | Runs all dev commands (`make bup`, `make seed`, ...) | Pre-installed on macOS/Linux |
| ngrok | Public HTTPS tunnel for the web app (Web Chat + Dashboard) | `brew install ngrok` |
| cloudflared | Public HTTPS tunnel for Telegram/WhatsApp webhooks | `brew install cloudflared` |
| An OpenAI account with billing enabled | Powers the agent, sentiment, briefing, STT, TTS | https://platform.openai.com |
| A Telegram account | To create the bot via @BotFather | — |
| A phone with WhatsApp | To test the WhatsApp Sandbox channel | — |

You do **not** need a Twilio account to run the demo — WhatsApp via the
**Twilio Sandbox** works with a free trial account (no credit card charge for
sandbox messaging).

---

## 2. Clone and create your `.env`

```bash
git clone <repo-url>
cd moei
cp .env.example .env
```

`.env` is gitignored — never commit it. `.env.example` is the template and
**is** committed; if you add a new setting, add it there too (with a safe
empty/example default).

---

## 3. Filling in `.env` — where to get every value

Open `.env` and fill in the values below. Variables marked **auto** are
written automatically by `make bup` — leave them blank.

### 3.1 Required — the platform won't work without these

| Variable | What it is | Where to get it |
|----------|------------|------------------|
| `POSTGRES_PASSWORD` | Password for the local Postgres container | Pick any strong password yourself — this is a local dev DB, not a shared one |
| `OPENAI_API_KEY` | Powers **everything AI**: the GPT-4o agent, GPT-4o-mini sentiment + briefing, Whisper STT, and TTS | 1. Go to https://platform.openai.com/api-keys <br> 2. Sign in / create an account <br> 3. **Settings → Billing** — add a payment method and add a few dollars of credit (the whole hackathon demo costs well under $5) <br> 4. **API keys → Create new secret key** — copy it immediately (shown once), paste as `OPENAI_API_KEY=sk-...` |
| `TELEGRAM_BOT_TOKEN` | Lets the channels service receive/send Telegram messages | 1. Open Telegram, search **@BotFather** <br> 2. Send `/newbot`, follow the prompts (choose a name and a unique username ending in `bot`) <br> 3. BotFather replies with a token like `123456789:AAH...` — paste as `TELEGRAM_BOT_TOKEN=...` <br> 4. Optional: `/setdescription`, `/setuserpic` to brand the bot for the demo |

### 3.2 Required for tunnels (so judges can use the live links)

| Variable | What it is | Where to get it |
|----------|------------|------------------|
| `NGROK_AUTH_TOKEN` | Authenticates your ngrok tunnel (free tier is enough) | 1. Sign up at https://dashboard.ngrok.com/signup (free) <br> 2. **Your Authtoken** page → copy the token <br> 3. Paste as `NGROK_AUTH_TOKEN=...` <br> 4. Also run once: `ngrok config add-authtoken <token>` (writes to ngrok's own config — `make ngrok`/`make bup` need this even if `.env` has the token) |
| `PUBLIC_BASE_URL` | Public HTTPS URL of the web app (port 3000) | **auto** — written by `make ngrok` (part of `make bup`). Leave empty. |
| `TELEGRAM_WEBHOOK_URL` | Public HTTPS URL Telegram sends updates to (channels service, port 8001) | **auto** — written by `make cloudflare` (part of `make bup`), then registered with Telegram by `make telegram-setup`. Leave empty. |

`cloudflared` needs **no account or token** for the quick tunnel used here —
just the binary installed (`brew install cloudflared`).

### 3.3 Optional — WhatsApp via Twilio Sandbox

| Variable | What it is | Where to get it |
|----------|------------|------------------|
| `TWILIO_AUTH_TOKEN` | Enables `X-Twilio-Signature` verification on `/whatsapp/webhook` (rejects forged requests) | 1. Sign up for a free trial at https://www.twilio.com/try-twilio (no credit card needed for the WhatsApp Sandbox) <br> 2. Console **Account Dashboard** → "Auth Token" (click "show") → copy <br> 3. Paste as `TWILIO_AUTH_TOKEN=...` |

Leaving `TWILIO_AUTH_TOKEN` empty is fine for a demo — the WhatsApp channel
still works, it just skips signature verification (anyone could POST to the
webhook, which is an accepted risk for a 48h hackathon — see
[DECISIONS.md](DECISIONS.md)).

**One-time: join the Twilio WhatsApp Sandbox from your phone**
1. In the Twilio Console, go to **Messaging → Try it out → Send a WhatsApp message**
2. It shows a sandbox number (e.g. `+1 415 523 8886`) and a join code like `join <two-words>`
3. From the WhatsApp account you'll demo with, send that join code to that number on WhatsApp
4. You'll get a confirmation reply — your number is now connected to the sandbox

This join step is **per phone number** and persists across restarts — you
only do it once per demo phone.

### 3.4 Inter-service / runtime

| Variable | Default | Notes |
|----------|---------|-------|
| `BACKEND_URL` | `http://backend:8000` | Used by the channels service to call the backend. Only change if running outside Docker Compose. |
| `POSTGRES_HOST` / `PORT` / `DB` / `USER` | `db` / `5432` / `moei` / `moei` | Fine as-is for Docker Compose |
| `REDIS_HOST` / `PORT` | `redis` / `6379` | Fine as-is for Docker Compose |
| `APP_ENV` | `development` | `production` disables SQLAlchemy query echo |
| `LOG_LEVEL` | `INFO` | `DEBUG` for verbose logs while debugging |

### 3.5 Present in `.env.example` but currently unused — safe to leave as-is

| Variable | Why it's there |
|----------|-----------------|
| `OPENAI_MODEL` | Not read by the app — the agent model (`gpt-4o`) and sentiment/briefing model (`gpt-4o-mini`) are hardcoded in `agent/core.py`, `agent/sentiment.py`, `agent/briefing.py`. Safe to ignore. |
| `TTS_VOICE` | Not read by the app — TTS voice (`nova`) is hardcoded in `voice/adapter.py`. Safe to ignore. |
| `ELEVENLABS_API_KEY` | Reserved for a possible future TTS upgrade (see ROADMAP.md tech debt). Not called anywhere currently. |

---

## 4. Starting everything

```bash
make bup
```

This single command runs, in order:

1. **`build`** — builds the `backend`, `channels`, `frontend` Docker images
2. **`up`** — starts all 5 containers (`db`, `redis`, `backend`, `channels`, `frontend`) via `docker compose up -d`
3. **`ngrok`** — starts an ngrok tunnel to port 3000 (the frontend) and writes the resulting HTTPS URL into `.env` as `PUBLIC_BASE_URL`
4. **`cloudflare`** — starts a `cloudflared` quick tunnel to port 8001 (the channels service) and writes `<tunnel>/telegram/webhook` into `.env` as `TELEGRAM_WEBHOOK_URL`; restarts the `channels` container so it picks up the new value
5. **`telegram-setup`** — calls `POST /telegram/setup` on the channels service, which registers `TELEGRAM_WEBHOOK_URL` with the Telegram Bot API
6. **`links`** — prints all current public URLs (web app, dashboard, Telegram bot, WhatsApp webhook)

First run takes 2–3 minutes (image downloads + builds). Subsequent
`make bup` runs are under 30 seconds.

**Why two tunnels?** ngrok's free tier gives one stable-enough tunnel for the
web app judges will click through during the demo. `cloudflared`'s quick
tunnel (no account needed) gives a second, independent HTTPS URL for
inbound webhooks (Telegram, WhatsApp) hitting the channels service on a
different port. Keeping them separate avoids ngrok free-tier connection
limits being shared between "judge browses the dashboard" and "Telegram
sends webhook updates".

### Tunnel URLs change every restart

Both ngrok and cloudflared issue a **new random URL every time they start**.
`make bup` handles re-registration automatically for:
- The web app link (`PUBLIC_BASE_URL`) — just re-share the new link
- Telegram (`telegram-setup` re-registers the webhook automatically)

It does **not** automatically re-register for:
- **WhatsApp** — Twilio's Sandbox has no setup API. You must manually paste
  the new webhook URL into the Twilio console after every `make bup`. See
  step 5 below.

---

## 5. Registering the WhatsApp webhook (after every `make bup`)

1. Run `make links` (also printed automatically at the end of `make bup`):
   ```
   ============================================================
   MOEI - live demo links
   ============================================================
   Web app:       https://abcd1234.ngrok-free.app
   Dashboard:     https://abcd1234.ngrok-free.app/dashboard
   Telegram bot:  https://t.me/your_bot_username
   WhatsApp hook: https://xyz9876.trycloudflare.com/whatsapp/webhook
     -> Twilio Console > Sandbox Settings > 'WHEN A MESSAGE COMES IN' (POST)
   ============================================================
   ```
2. Copy the `WhatsApp hook` URL
3. In the Twilio Console: **Messaging → Try it out → Send a WhatsApp message → Sandbox settings**
4. Paste the URL into **"WHEN A MESSAGE COMES IN"**, method **POST**, click **Save**

That's it — messages sent to the Sandbox number now reach
`POST /whatsapp/webhook` and get an instant TwiML reply.

---

## 6. Verifying everything works

```bash
make ps
```

Expected output (all green):

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

If anything is `"error"` — check `make logs-backend` / `make logs-channels`
and fix it **before** writing or testing any new code (see CLAUDE.md).

Then:
```bash
make seed   # populate realistic demo conversations (~$0.10 in OpenAI usage)
make test   # run integration tests against the running stack
```

### Smoke test each channel

| Channel | How to test |
|---------|-------------|
| Web Chat | Open `http://localhost:3000`, enter a phone number on the phone gate, send a message |
| Telegram | Open `https://t.me/<your_bot_username>`, send `/start`, tap "Share phone number", chat |
| WhatsApp | Send a message to the Twilio Sandbox number from a phone that joined the sandbox |
| Voice | In Web Chat, tap 🎤, speak, wait for the audio reply |
| Dashboard | Open `http://localhost:3000/dashboard` — should show metrics, charts, and (after the above) the new customer in **Customer 360** |

If you used the **same phone number** for Web Chat and WhatsApp, `/api/customers`
should show **one** customer with both channels listed — this is the core
"unified identity" story for the demo.

---

## 7. Stopping / resetting

```bash
make down     # stop containers, keep all data (Postgres + Redis volumes)
make fclean   # stop containers AND delete all data — fresh start
```

Use `make fclean && make bup && make seed` if you change `backend/app/models.py`
(there's no migration tool yet — see ROADMAP.md tech debt) or if the demo
data gets messy and you want a clean slate.

---

## 8. Demo day checklist

1. `make bup` — wait for "ngrok tunnel ready" and "Cloudflare tunnel ready" lines, then the links banner
2. `make ps` — confirm all green
3. Re-register the WhatsApp webhook in the Twilio console (step 5 above) — **do this every time**, the URL changed
4. `make seed` — populate the dashboard with realistic data
5. Open the printed `Web app` and `Dashboard` links in a browser tab each — these are what you'll show on screen
6. Do one quick end-to-end message on each channel to confirm everything is warm (LLM cold-start, Redis, etc.)
7. Run through the demo script in [DEMO_REFERENCES.md](DEMO_REFERENCES.md)

---

## 9. Troubleshooting

| Problem | Fix |
|---------|-----|
| `make ngrok` fails with "no HTTPS tunnel — is ngrok authenticated?" | Run `ngrok config add-authtoken <token>` — the `.env` value alone isn't enough, ngrok also needs its own local config |
| `cloudflared: command not found` | `brew install cloudflared` |
| Telegram bot doesn't respond | `make telegram-setup` to re-register the webhook; check `TELEGRAM_BOT_TOKEN` is correct |
| WhatsApp messages get no reply | Re-paste the current `/whatsapp/webhook` URL (from `make links`) into the Twilio Sandbox console — it changes every `make bup` |
| `/health` shows `"db": "error"` or `"redis": "error"` | `make logs-backend` — usually means the containers raced on startup; `make down && make up` |
| OpenAI errors (401 / quota) | Check `OPENAI_API_KEY` is correct and the account has billing/credit enabled |
| Voice mic does nothing in browser | Microphone access requires `localhost` or HTTPS — use `http://localhost:3000`, not the LAN IP |

For developer-facing issues (architecture, code structure, API reference),
see [DEV_DOC.md](DEV_DOC.md).
