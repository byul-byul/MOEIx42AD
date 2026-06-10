# Demo & Pitch Reference — MOEI AI Customer Engagement Agent

**Audience:** the presenter. Everything you need to prepare the pitch, run
the live demo, and answer judges' questions — in one place.

**TL;DR elevator pitch:**
> "We built one AI agent — not four chatbots. A citizen can start a
> conversation on Telegram, continue it on WhatsApp, and walk into a branch,
> and the system already knows who they are, what they asked for, how
> frustrated they are, and what a human agent should do next. That's the
> 'unified omnichannel' the challenge asks for — and we can prove it live by
> messaging from two different apps with the same phone number."

---

## 1. Problem statement

MOEI (Ministry of Energy and Infrastructure, Abu Dhabi) — like most
utility/government service providers — runs customer service across
disconnected channels: a phone hotline, a website form, maybe a WhatsApp
number, maybe a Telegram bot. Each channel is its own silo.

**Pain points this creates:**

1. **Customers repeat themselves.** A citizen reports a power outage on
   WhatsApp, then calls the hotline an hour later — the agent has no idea
   the WhatsApp message ever happened. Frustration compounds.
2. **Agents work blind.** A human agent picking up a conversation sees only
   that one channel's history — no context on prior tickets, prior tone, or
   how urgent this really is.
3. **Unhappy customers go unnoticed until they escalate loudly.** There's no
   systematic way to detect "this person is getting angry" before it becomes
   a complaint to leadership or the media.
4. **Leadership has no real-time visibility.** Ticket volumes, sentiment
   trends, and channel mix live in spreadsheets compiled after the fact, not
   a live operational picture.
5. **24/7 bilingual (Arabic/English) coverage is expensive.** Routine
   inquiries (bill status, outage reports, meter readings) consume agent
   hours that could go to genuinely complex cases.

**Value / economic effect of solving this:**

- **Deflection:** routine inquiries (bill status, ticket status, general
  procedures) are fully handled by AI, 24/7, in both languages — no agent
  time spent.
- **Faster resolution:** when a human agent does step in, the AI briefing
  (cross-channel summary + urgency + recommended action) means zero ramp-up
  time per case.
- **Proactive retention:** sentiment alerts surface at-risk customers to
  leadership *before* they escalate publicly — fewer complaints, better
  satisfaction scores.
- **Operational visibility:** leadership gets a live dashboard instead of
  end-of-day reports — faster staffing and process decisions.

---

## 2. What we built — architecture overview

```
┌─────────────┐
│  Telegram   │──┐
├─────────────┤  │
│  WhatsApp   │──┤   Channels Service (port 8001)
├─────────────┤  ├──▶  Dumb adapters: parse → IncomingMessage → POST /api/message
│  Voice (mic)│──┤
└─────────────┘  │
┌─────────────┐  │
│  Web Chat   │──┘ (also connects directly via WebSocket)
└─────────────┘
        │
        ▼
┌────────────────────────────────────────────────────────┐
│  Backend Service (port 8000)                            │
│  LangGraph + GPT-4o agent  (channel-agnostic)           │
│  ├─ Sentiment classification (GPT-4o-mini)              │
│  ├─ Cross-channel identity resolution (resolve_user)    │
│  └─ AI agent briefing for human agents (GPT-4o-mini)    │
└───────────┬───────────────────────────────┬────────────┘
            │                               │
   ┌────────▼────────┐             ┌────────▼────────┐
   │  Postgres        │             │  Redis           │
   │  customers,      │             │  session context │
   │  users, tickets, │             │  (TTL 1h, AOF)   │
   │  messages        │             │                  │
   └──────────────────┘             └──────────────────┘
            │
   ┌────────▼─────────────────────────────────────────┐
   │  Frontend (port 3000) — React                     │
   │  Web Chat + voice mic | Operations Dashboard:     │
   │  KPIs, charts, sentiment alerts, AI co-pilot,     │
   │  Customer 360 (cross-channel briefing)            │
   └────────────────────────────────────────────────────┘
```

**The one architectural idea that ties it all together:** every channel
captures the customer's **phone number** (Telegram via a one-tap
"share contact" button, WhatsApp natively, Web Chat via a one-time "phone
gate", Voice via the same gate). `resolve_user()` links every `User` row to
a single `Customer` row keyed by phone. That one join is what makes
"the same person across 4 channels = one profile" real, not simulated.

---

## 3. Where the AI is — the part judges will grade hardest

This is an **AI hackathon**, so be explicit: every box below is a real model
call, not a hardcoded response. Here's the full inventory:

| # | AI component | Model | What it does | Where |
|---|--------------|-------|---------------|-------|
| 1 | **Conversational agent** | GPT-4o via LangGraph (ReAct loop, `temperature=0.3`) | Understands the customer's request in **English or Arabic** (auto-detected, no language flag needed), holds context across turns, decides whether to call a tool | `backend/app/agent/core.py` |
| 2 | **Tool use (function calling)** | Same GPT-4o agent, bound to 2 tools | `create_ticket` — opens a support ticket when the customer reports a problem; `get_ticket_status` — looks up an existing ticket by number. The model *decides* when to call these — not a keyword match. | `backend/app/agent/tools.py` |
| 3 | **Sentiment classification** | GPT-4o-mini | Every customer message is classified `positive` / `neutral` / `negative` in real time — feeds the dashboard sentiment chart **and** the alert banner | `backend/app/agent/sentiment.py` |
| 4 | **Escalation detection** | Rule-based safety net (English + Arabic keyword list: gas leak, fire, electrical hazard, emergency / تسرب غاز، حريق، خطر كهربائي، طوارئ) layered on top of the LLM's own judgment | Guarantees safety-critical messages are flagged even if the LLM's prose doesn't trigger it | `backend/app/agent/core.py` |
| 5 | **Cross-channel AI case briefing** | GPT-4o-mini, **structured JSON output** (`response_format: json_object`) | Given a customer's *entire cross-channel history*, produces `{summary, urgency: low/medium/high, recommended_action}` — this is effectively an **AI case manager** for the human agent | `backend/app/agent/briefing.py` |
| 6 | **Speech-to-text** | OpenAI Whisper API | Converts the browser microphone recording to text before it hits the same agent pipeline | `backend/app/channels/voice/adapter.py` |
| 7 | **Text-to-speech** | OpenAI TTS (`tts-1`, voice `nova`) | Converts the agent's reply back to spoken audio | `backend/app/channels/voice/adapter.py` |
| 8 | **AI Co-pilot suggestions** | Reuses the agent's own generated replies (component 1) | Live feed for human agents of "here's what the AI would say / did say" — a ready-made response to approve or adapt | `backend/app/dashboard/metrics.py` (`/api/copilot`) |

**Why this is more than "a chatbot with a UI":**

- The agent **uses tools** — it's not pattern-matching, it's reasoning about
  when a ticket is needed and creating it autonomously.
- The briefing model produces **structured, validated output** with a
  defensive fallback (`urgency: medium` + safe default text if the JSON is
  malformed or the call fails) — the same pattern used for sentiment. This
  is a production-grade reliability pattern, not a demo hack.
- **Sentiment → alert → AI briefing → human action** is a closed loop: AI
  doesn't just answer questions, it actively triages the human team's
  workload.
- **Bilingual by design**, not by translation step — the same GPT-4o call
  handles Arabic and English because the system prompt instructs it to
  "reply in the same language the customer uses."

---

## 4. Demo script (3 minutes)

Run `make seed` beforehand so the dashboard isn't empty, **and** do the live
steps below with a phone number that is *not* in the seed data, so the
"merge" is visibly new.

> Pick one real phone number for yourself before the demo (e.g.
> `+9715xxxxxxxx`). You'll use it on **two different channels** — that's the
> whole trick.

### Step 1 — Telegram, in Arabic (≈30s)
- Open the bot, send `/start`
- Tap **"📱 Share phone number"** (one tap — say out loud: *"this links my
  Telegram identity to a phone number — the universal key across every
  channel"*)
- Send (Arabic): *"عندي انقطاع في الكهرباء منذ ٣ أيام"* ("I've had a power
  outage for 3 days")
- Agent replies in Arabic, **creates a ticket** (point out the ticket badge)

### Step 2 — WhatsApp, same phone number, in English (≈30s)
- From the **same phone**, message the Twilio Sandbox number:
  *"This is unacceptable, I've called twice already and nothing happened!"*
- Agent replies — point out: *"different channel, different language, same
  customer — and the system knows it."*

### Step 3 — Dashboard: sentiment alert → Customer 360 (≈60s)
- Switch to the dashboard (already open in a tab)
- The **🚨 Negative sentiment detected** banner appears within ~5s (poll
  interval) showing the WhatsApp message
- Click **"View Customer"** → scrolls to **Customer 360**
- Point out:
  - **Channel badges**: this one customer has both `telegram` and
    `whatsapp` — *"one profile, two channels, same phone number"*
  - **AI summary** (GPT-4o-mini): a 1–3 sentence brief of the whole
    situation
  - **Urgency badge**: `high` — driven by the AI, not a manual flag
  - **Recommended action**: a concrete next step for the agent
  - **Conversation timeline**: every message, every channel, oldest first
- Click **Escalate** on the open ticket — watch the **Escalated** KPI
  increment live

### Step 4 — Voice (≈30s)
- Open Web Chat, tap 🎤, ask a question out loud (English or Arabic)
- Agent transcribes (Whisper), answers, and **speaks the answer back** (TTS)

### Step 5 — Leadership view (≈30s)
- Scroll back to the top: **Active Sessions, Total/Open/Escalated Tickets**,
  **Messages by Channel**, **Tickets by Status**, **Customer Sentiment**
  charts — all live, all from real data generated in the last 2 minutes
- Close with: *"Everything you just saw — the ticket, the sentiment
  classification, the AI summary, the urgency score, the voice transcript —
  is a live model call. Nothing here is canned."*

---

## 5. Why this team / product deserves 1st place

**1. We solved the *actual* challenge, not a simplified version of it.**
"Omnichannel with shared context" is the hard requirement most teams will
fake with a shared session ID typed manually between tabs. We built a real
identity model (`customers` table, phone-based linking, `resolve_user()`)
and can **prove it live** by messaging from two different apps.

**2. AI does real work, not just Q&A.** The sentiment → alert →
AI-generated briefing → human action loop turns the AI into an operational
tool for the *business*, not just a customer-facing toy. This directly
answers "how is AI used" with concrete, inspectable model calls — including
structured JSON output with validation and fallbacks, which shows
engineering maturity beyond a hackathon prototype.

**3. Truly bilingual, by design.** Arabic and English are handled by the
same model, same prompt, same code path — appropriate for the UAE context
and the ministry's actual user base, not bolted on.

**4. Clean, extensible architecture.** `BaseChannel` adapter pattern means
adding a 5th channel (Twilio Voice, SMS, ...) is a few hours of work, not a
rewrite — the agent is 100% channel-agnostic. This is a system you could
actually start hardening for production on Monday.

**5. We know exactly what's left — and that's a feature, not a bug.** See
the roadmap below: every "missing" piece is identified, scoped, and
estimated. That's the difference between "we ran out of time" and "we made
deliberate scope calls under a 48h constraint and know the path forward."

---

## 6. Roadmap — what's next (a.k.a. the tech debt, framed honestly)

We made explicit, documented trade-offs to ship a working, demo-able product
in 48 hours. Each item below was a conscious call — not an oversight — and
each has a clear path to production. Presenting this section signals a team
that thinks past the demo.

### Near-term (Phase 8 — production hardening)

| Item | Why we deferred it | What "done" looks like |
|------|---------------------|--------------------------|
| **WebSocket authentication** | Demo runs on trusted local/tunnel network; auth adds complexity with zero demo-visible benefit | JWT/signed token on the `/ws/{session_id}` handshake (~2h) |
| **Chat history DB fallback** | Redis (1h TTL, AOF-persisted) covers every demo scenario | `GET /api/session/{id}` falls back to `messages` table if the Redis key expired (~1h) |
| **Database migrations (Alembic)** | `Base.metadata.create_all()` + `make fclean` is faster to iterate on during a 48h build | Initial Alembic revision from current models, so schema changes don't require dropping data (~1h) |
| **Rate limiting** | No abuse vector in a judged demo | `slowapi` middleware on `/api/message` and `/ws/` (~1h) |

### Medium-term (Phase 8/9 — deeper omnichannel)

| Item | Why we deferred it | What "done" looks like |
|------|---------------------|--------------------------|
| **Account linking without a phone number** | Phone-based identity covers the primary demo story (WhatsApp + Telegram + Web with the same number); a customer who starts on web *without* a phone gets a separate profile | A "link my WhatsApp/Telegram" flow — one-time code sent on the new channel, entered on the existing one, merging `User` rows under one `Customer` (~2h) |
| **Real prosody/audio-based voice emotion detection** | Risky to get right in 48h; transcript-based sentiment (already built) gives an honest, working "voice sentiment" today | Analyze pitch/pace/energy from the raw audio in `voice/adapter.py`, alongside transcript sentiment (~3h+) |

### Longer-term (Phase 9 — telephony & scale)

| Item | Why we deferred it | What "done" looks like |
|------|---------------------|--------------------------|
| **Twilio Voice (real phone calls)** | Browser-mic voice already demonstrates the full STT→Agent→TTS pipeline required by the challenge; real telephony is additive | TwiML voice webhook + Twilio's STT/Gather → `run_agent()` → TTS `Say`, reusing the same phone-based `Customer` context as WhatsApp (~3h) |
| **Cloud deployment (Railway/Render)** | Docker Compose is sufficient and faster for a local/tunnel-based demo | Each service as a managed web service; Postgres/Redis as managed add-ons; env vars via platform UI |

> Full detail and effort estimates: [ROADMAP.md](ROADMAP.md).

---

## 7. Anticipated questions & answers

**"Is the voice channel a real phone call?"**
No — it's a browser microphone in the web chat, implementing the full
**STT → Agent → TTS** pipeline the challenge specifies. We frame it as a
"voice-enabled interface" demonstrating the pipeline; real telephony
(Twilio Voice) is the next step (see roadmap) and would reuse the exact same
agent and customer-identity logic.

**"How does cross-channel identity actually work? Is it faked for the demo?"**
No — it's a real database join. `customers.phone` is the universal key;
every `users` row optionally links to one via `customer_id`; every `messages`
row links to a `users` row. `/api/customers/{id}/briefing` performs a real
SQL join across `messages → users → customers`. You can verify live by
messaging from two channels with the same number.

**"How accurate is the sentiment / urgency classification?"**
Both use OpenAI models (GPT-4o-mini) with constrained output — sentiment is
a single-word classification from a fixed set; the briefing uses JSON mode
with a fixed schema and a safe fallback (`urgency: medium`) if parsing
fails. It's a real classifier, with the same reliability pattern you'd want
in production (graceful degradation, never a hard error to the user).

**"What does this cost to run?"**
The full demo (8 seeded conversations + live demo messages + voice +
briefings) costs well under $1 in OpenAI usage. At scale, GPT-4o-mini calls
(sentiment, briefing) are the cheapest and most frequent; GPT-4o (agent) and
Whisper/TTS (voice) are the larger per-interaction costs — but still far
below the cost of a human agent handling the same routine inquiry.

**"Is this production-ready?"**
The architecture is — `BaseChannel` adapters, channel-agnostic agent,
async DB/Redis. What's not yet done is explicitly tracked (section 6 above):
auth, migrations, rate limiting. None of these are architectural risks —
they're scoped follow-ups.

**"Why phone number and not a login/account system?"**
A login system (passwords, sessions, account recovery) is real product
surface area that doesn't exist for most government-service customers
today and wasn't buildable in 48h without cutting something that
demonstrates AI. Phone number is already the universal identifier on
WhatsApp and Telegram (once shared) — using it as the customer key gets us
"unified identity" with a single new field, not a new subsystem. It's a
deliberate MVP simplification with a documented upgrade path (account
linking, above).

---

## 8. Quick links for the presenter

- Full demo links (after `make bup`): run `make links`
- Step-by-step setup if something needs restarting: [DEPLOYMENT.md](DEPLOYMENT.md)
- Architecture / API detail for technical questions: [DEV_DOC.md](DEV_DOC.md)
- End-user walkthrough of every screen: [USER_DOC.md](USER_DOC.md)
- Full tech-debt list with effort estimates: [ROADMAP.md](ROADMAP.md)
- Architecture decisions and trade-off reasoning: [DECISIONS.md](DECISIONS.md)
