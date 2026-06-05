---
name: tech-debt
description: Known technical debt and deferred decisions in the MOEI project
metadata:
  type: project
---

## Cross-channel identity linking

**What:** Same person writing from Telegram and web chat gets different session_ids (`telegram_123` vs `webchat_abc`). No link between them — separate Redis history, separate DB rows.

**Why deferred:** Hackathon time constraint. For the demo, presenter manually enters the same session_id in the web chat input field.

**Proper fix:** `identities` table linking multiple `(channel, channel_user_id)` pairs to a single internal `user_id`. Users table currently only populated on ticket creation, not on first message.

**How to apply:** Flag this if the user asks about cross-channel context or user identity. Estimate ~2-3h to implement properly.
