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

## [DECIDED] Cross-channel session identity — shared vs. separate

**Status:** decided — separate for now, deferred to post-hackathon

**Decision:** Each channel generates its own `session_id` (`telegram_xxx`, `webchat_xxx`). No cross-channel identity linking.

**Demo workaround:** Presenter can type the Telegram session ID manually into the web chat to demonstrate shared context.

**Full fix:** `identities` table (see `ROADMAP.md` tech debt). Estimated ~3h.

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

## [OPEN] WhatsApp — required for MVP or bonus?

**Status:** open — confirm with team

**Question:**  
WhatsApp is the 4th channel in the requirements. We have a stub (`channels/whatsapp/adapter.py`).  
Is a working WhatsApp integration required for the submission, or is the architecture + stub sufficient?

**Context:**  
WhatsApp Cloud API requires a Meta business account, phone number verification, and webhook with HTTPS. Setup takes 2-4h outside of coding time.

**Options:**
1. Implement fully (same pattern as Telegram, ~2h code + Meta setup time)
2. Show the stub + architecture in the pitch ("follows the same adapter pattern, can be activated with credentials")
3. Use WhatsApp Business Test number via Meta Developer sandbox

**Recommendation:** Confirm with team. If any team member already has a Meta developer account, go for option 1. Otherwise option 2 is defensible given the architecture.
