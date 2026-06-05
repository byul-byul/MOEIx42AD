#!/usr/bin/env python3
# /scripts/seed_demo.py
"""
Seed realistic demo conversations into the running backend.
Run: python scripts/seed_demo.py
Requires: services up (make up). Uses real GPT-4o — costs ~$0.10.
"""
import asyncio
import random
import httpx

BACKEND = "http://localhost:8000"

CONVERSATIONS = [
    # (channel, user_id, messages)
    ("webchat", "web_demo_1", [
        "Hello, I'd like to check my electricity bill status.",
        "My account number is 123456789.",
        "Can I pay it online?",
    ]),
    ("telegram", "tg_demo_2", [
        "مرحباً، فاتورة الكهرباء عندي مرتفعة جداً هذا الشهر",
        "كيف أتحقق من تفاصيل الاستهلاك؟",
        "شكراً لمساعدتك",
    ]),
    ("webchat", "web_demo_3", [
        "My power went out 2 hours ago and hasn't come back. This is an emergency!",
        "I have elderly parents at home who need medical equipment.",
        "Please create an urgent ticket immediately.",
    ]),
    ("telegram", "tg_demo_4", [
        "Hi, I want to connect new service to my building",
        "It's a commercial property in Abu Dhabi",
        "What documents do I need?",
    ]),
    ("webchat", "web_demo_5", [
        "سقوط شجرة على كابل الكهرباء أمام منزلي",
        "هل هذا خطر؟",
        "أريد تقديم بلاغ طارئ",
    ]),
    ("webchat", "web_demo_6", [
        "What are the MOEI office hours?",
        "Is there a 24/7 emergency number?",
    ]),
    ("telegram", "tg_demo_7", [
        "My meter reading seems wrong — it jumped 300 units in one week",
        "Please investigate and fix this",
    ]),
    ("webchat", "web_demo_8", [
        "I'm very happy with the fast response I got last time, thank you!",
        "I just wanted to check my ticket status: #1",
    ]),
]


async def send_message(client: httpx.AsyncClient, session_id: str, channel: str, user_id: str, text: str):
    payload = {
        "session_id": session_id,
        "channel": channel,
        "user_id": user_id,
        "text": text,
        "language": "ar" if any(ord(c) > 0x600 for c in text) else "en",
    }
    try:
        r = await client.post(f"{BACKEND}/api/message", json=payload, timeout=30)
        r.raise_for_status()
        data = r.json()
        sentiment = data.get("sentiment", "?")
        ticket = f" | ticket #{data['ticket_id']}" if data.get("ticket_id") else ""
        print(f"  [{channel}] {user_id}: {text[:50]!r} → sentiment={sentiment}{ticket}")
    except Exception as e:
        print(f"  ERROR {session_id}: {e}")


async def main():
    print(f"Seeding demo data into {BACKEND}")
    print("=" * 60)

    # Verify backend is up
    async with httpx.AsyncClient() as client:
        try:
            r = await client.get(f"{BACKEND}/health", timeout=5)
            health = r.json()
            print(f"Health: {health}")
            if health.get("backend") != "ok":
                print("Backend not healthy — aborting.")
                return
        except Exception as e:
            print(f"Cannot reach backend: {e}\nRun 'make up' first.")
            return

        print()
        for channel, user_id, messages in CONVERSATIONS:
            session_id = f"{channel}_{user_id}"
            print(f"Session: {session_id}")
            for text in messages:
                await send_message(client, session_id, channel, user_id, text)
                await asyncio.sleep(random.uniform(0.3, 0.8))
            print()

    print("=" * 60)
    print("Demo seed complete. Open http://localhost:3000/dashboard to see results.")


if __name__ == "__main__":
    asyncio.run(main())
