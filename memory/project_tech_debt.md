---
name: tech-debt
description: Known technical debt and deferred decisions in the MOEI project
metadata:
  type: project
---

## Users table not populated for general inquiries

**What:** `users` table only gets a row when a ticket is created. Users who only chat without creating a ticket are invisible in the DB.

**Why deferred:** Not critical for demo — messages are tracked with session_id. No dashboard metric depends on user count yet.

**Proper fix:** Create/upsert a user row on every first message in a session.

**How to apply:** Flag if user count or user-level analytics are needed.

---

## Chat history falls back to Redis only (not DB)

**What:** `GET /api/session/{session_id}` reads from Redis (TTL 1h). If Redis is restarted, history is lost even though messages exist in the DB `messages` table.

**Why deferred:** For the hackathon demo Redis won't restart. DB restore logic adds complexity.

**Proper fix:** Fall back to querying `messages` table by `session_id` if Redis key is missing.

**How to apply:** Flag if Redis data loss is a concern (production readiness).

---

## WebSocket endpoint has no authentication

**What:** Any client knowing a `session_id` can connect to `/ws/{session_id}` and read or inject messages into that session.

**Why deferred:** Internal demo, not public-facing.

**Proper fix:** Token-based auth (JWT or signed session token) on the WebSocket handshake.

**How to apply:** Required before any public/production deployment.

---

## Cross-channel identity linking

**What:** Same person writing from Telegram and web chat gets different session_ids (`telegram_123` vs `webchat_abc`). No link between them — separate Redis history, separate DB rows.

**Why deferred:** Hackathon time constraint. For the demo, presenter manually enters the same session_id in the web chat input field.

**Proper fix:** `identities` table linking multiple `(channel, channel_user_id)` pairs to a single internal `user_id`. Users table currently only populated on ticket creation, not on first message.

**How to apply:** Flag this if the user asks about cross-channel context or user identity. Estimate ~2-3h to implement properly.
