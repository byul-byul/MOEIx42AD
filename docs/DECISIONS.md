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

**Telegram follow-up (closed 2026-06-10):** Telegram now participates in the
same identity scheme. On `/start`, the bot shows a one-tap "📱 Share phone
number" button (`request_contact`); the resulting `Contact.phone_number` is
sent through `resolve_user()` like any other channel, so a customer who
shares their phone on Telegram links into the same `Customer` row as
WhatsApp/web chat.

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

**Closed (2026-06-10):** `X-Twilio-Signature` verification is now implemented
— if `TWILIO_AUTH_TOKEN` is set, every `/whatsapp/webhook` request is
validated with `twilio.request_validator.RequestValidator` and rejected
(403) if the signature doesn't match. Left optional (empty token = no check)
so the Sandbox demo works without registering Twilio credentials.

---

## [DECIDED] Real prosody/audio-based voice emotion detection

**Status:** closed (2026-06-11)

**Context:** team feedback asked for real-time voice emotion/tone detection
("if a client sounds sad, raise an alert"). For P0, voice emotion reused the
existing transcript-based `classify_sentiment()` — the same sentiment
pipeline as text channels, applied to the Whisper transcript. This was
honest ("voice sentiment analysis") and shipped with zero new risk, but it
can't tell *how* something was said — only what was said.

**Closed (2026-06-11):** added `agent/prosody.py` — a real signal-processing
pass over the raw recording, run alongside Whisper STT in `voice/adapter.py`.
It decodes the browser's webm/opus audio to 16kHz mono PCM via `ffmpeg`
(already in the backend image for Whisper — no new system deps), then
computes RMS loudness and an autocorrelation-based F0 pitch estimate (80-400
Hz) using only `numpy`. These are mapped to a coarse `tone`:
`agitated | calm | flat`.

This is a **heuristic, not a trained ML model** — thresholds
(`_LOUD_RMS`, `_HIGH_PITCH_HZ`, `_HIGH_PITCH_VARIANCE_HZ`) are tuned for a
single adult voice on a laptop/phone mic, not validated against a labeled
emotion dataset. We chose this over a real prosody/emotion model
(e.g. openSMILE, a wav2vec2 emotion classifier) because those add heavy
dependencies (torch, audio feature libs) and meaningful build time/size risk
on demo day, for a result that judges can't verify is "more correct" than a
simple heuristic in a 3-minute demo.

`voice_tone` is stored on the user `Message` row, surfaced in
`/api/copilot` and `/api/customers/{id}/briefing`, shown as a badge in the
dashboard (Co-pilot panel + conversation timeline), and fed into the
cross-channel briefing prompt (`agent/briefing.py`) — an "agitated" tone
nudges the AI briefing toward higher urgency even if the transcript wording
is neutral. Analysis runs in parallel with Whisper STT (`asyncio.gather`)
and fails safe (`None`) on any error, same defensive pattern as
`classify_sentiment`/`generate_briefing`.
