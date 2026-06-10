# DECISIONS.md — Open Questions & Architecture Decisions

This file tracks open questions for team discussion, architectural choices made, and decisions pending review.

Format: each entry has a **status** — `open` (needs team input), `decided` (resolved), or `deferred` (intentionally postponed).

---

## [OPEN] Voice channel — browser mic vs. phone call

**Status:** open — discuss with team before demo

**Question:**  
The hackathon requirement says *"Voice (STT → Agent → TTS)"*.  
We implemented this as a browser microphone button in the web chat UI.  
Is this acceptable, or do the judges expect a phone-based voice channel (Twilio/Vonage)?

**What we built:**  
Browser 🎤 → WebM audio → `POST /voice/message` → Whisper STT → Agent → OpenAI TTS → MP3 played in browser.  
Stored in DB as `channel = "voice"`. Architecturally a separate channel adapter.

**Arguments for (browser mic is fine):**  
- Requirement says "Voice (STT → Agent → TTS)" — not "phone call"
- The full STT → Agent → TTS chain is implemented correctly
- Live demo is stronger: judge clicks mic and hears the response immediately
- Twilio adds telecom complexity, phone numbers, cost — out of scope for 48h

**Arguments against:**  
- MOEI context is government customer service — customers call, they don't open a web page
- Judges may see it as "voice input in web chat" rather than an independent voice channel
- Demo scenario says "Customer calls" — implies telephony

**Options if judges push back:**  
1. Keep as-is and explain the architecture (STT/TTS chain is the point, not the transport)
2. Add Twilio programmable voice as a thin wrapper around the same `/voice/message` endpoint (~3h)
3. Frame it as "voice interface" rather than "voice channel" in the pitch

**Recommendation:** Keep as-is. Clarify framing in the pitch: "voice-enabled web interface demonstrating the full STT→Agent→TTS pipeline." Revisit only if a team member has Twilio experience and time.

---

## [DECIDED] Whisper — local model vs. OpenAI API

**Status:** decided — using OpenAI API

**Decision:** Use `openai.audio.transcriptions` (Whisper API) instead of local `openai-whisper` package.

**Why:** Local Whisper requires `torch` (2GB+), `ffmpeg`, CUDA for speed. Build time and image size are unacceptable for a 48h hackathon. OpenAI API gives the same quality with zero local dependencies.

**Trade-off:** Costs ~$0.006/minute of audio. Acceptable for demo scale.

---

## [DECIDED] Cross-channel session identity — phone number as universal key

**Status:** decided (2026-06-10) — superseded the "separate for now" decision below

**Decision:** Each channel still generates its own `session_id`
(`telegram_xxx`, `webchat_xxx`, `whatsapp_+9715xxx`), but every `User` row can
now link to a shared `Customer` row keyed by phone number
(`users.customer_id` → `customers.phone`). WhatsApp always carries the phone
number (it's the channel address); web chat asks for it once on first load
("phone gate", stored in `localStorage`); voice carries it the same way.
`resolve_user()` (`backend/app/agent/identity.py`) does the find-or-create and
linking on every message.

**Demo:** message the WhatsApp sandbox and the web chat with the same phone
number — `/api/customers` shows one customer with both channels, and
`/api/customers/{id}/briefing` returns the merged cross-channel history.

**Deferred:** "link my existing Telegram/WhatsApp" flow for users who didn't
start with a phone number — see `ROADMAP.md` tech debt.

~~Previous decision (kept for history): each channel generates its own
`session_id` with no cross-channel linking; presenter manually re-typed the
Telegram session ID into web chat to fake shared context.~~

---

## [OPEN] Co-pilot for human agents — scope for demo

**Status:** open — needs scope decision before Phase 6

**Question:**  
The demo scenario explicitly includes: *"Human agent sees AI co-pilot suggestions in real time."*  
What is the minimum viable co-pilot for the hackathon?

**Options:**
1. **Minimal (recommended):** A panel in the Dashboard showing the last 5 agent responses as "suggested replies" that a human operator could copy-paste. No new backend logic needed.
2. **Medium:** A dedicated `/copilot` page with live WebSocket feed of ongoing conversations + AI-suggested next response.
3. **Full:** Human agent can override AI response before it's sent to the customer.

**Recommendation:** Option 1. Reuses existing `/api/metrics` data, ships in ~2h, convincing for demo.

---

## [DECIDED] WhatsApp — Twilio Sandbox instead of Meta Cloud API

**Status:** decided (2026-06-10)

**Decision:** `channels/whatsapp/adapter.py` implements `BaseChannel` (same
pattern as Telegram) on top of the **Twilio WhatsApp Sandbox**: `POST
/whatsapp/webhook` receives `From`/`Body` form fields, replies synchronously
via TwiML (`MessagingResponse`) — no outbound API calls or Twilio credentials
needed. Reuses the existing `make cloudflare` tunnel
(`https://<tunnel>.trycloudflare.com/whatsapp/webhook`), registered manually
in the Twilio Sandbox console (no setup API like Telegram's).

**Why not Meta Cloud API:** requires a verified business account and
phone-number setup that takes hours outside of coding time. Twilio Sandbox
works immediately with a $15 trial credit and the phone number it sends
*is* the Customer Identity key (see cross-channel identity decision above).

**Removed:** unused Meta-oriented `WHATSAPP_TOKEN` / `WHATSAPP_PHONE_NUMBER_ID`
/ `WHATSAPP_VERIFY_TOKEN` settings.

**Tech debt:** Twilio webhook signature verification (anyone can POST to
`/whatsapp/webhook` right now — acceptable for a hackathon demo, not for prod).

---

## [DEFERRED] Real prosody/audio-based voice emotion detection

**Status:** deferred — tech debt

**Context:** team feedback asked for real-time voice emotion/tone detection
("if a client sounds sad, raise an alert"). For P0, voice emotion reuses the
existing transcript-based `classify_sentiment()` — the same sentiment
pipeline as text channels, applied to the Whisper transcript. This is honest
("voice sentiment analysis") and ships with zero new risk.

**Full fix:** analyze the raw audio (pitch, pace, energy) via a
prosody/emotion model, in addition to transcript sentiment. Out of scope for
the hackathon timeline.
