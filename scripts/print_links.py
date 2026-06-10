#!/usr/bin/env python3
# /scripts/print_links.py
"""Print the current public demo links (web app, dashboard, Telegram bot,
WhatsApp webhook). Reads URLs from .env, which `make ngrok`/`make cloudflare`
update on every `make bup` (tunnel URLs are not stable across restarts).
Run: python3 scripts/print_links.py (called automatically by `make bup`)
"""
import json
import re
import urllib.request

ENV_FILE = ".env"


def read_env() -> dict[str, str]:
    env = {}
    with open(ENV_FILE) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            env[key.strip()] = value.strip()
    return env


def telegram_bot_username(token: str) -> str | None:
    if not token:
        return None
    try:
        with urllib.request.urlopen(f"https://api.telegram.org/bot{token}/getMe", timeout=5) as resp:
            return json.load(resp)["result"]["username"]
    except Exception:
        return None


def main() -> None:
    env = read_env()
    web = env.get("PUBLIC_BASE_URL", "")
    telegram_webhook = env.get("TELEGRAM_WEBHOOK_URL", "")
    whatsapp_webhook = re.sub(r"/telegram/webhook$", "/whatsapp/webhook", telegram_webhook)
    bot_username = telegram_bot_username(env.get("TELEGRAM_BOT_TOKEN", ""))

    print()
    print("=" * 60)
    print("MOEI - live demo links")
    print("=" * 60)
    print(f"Web app:       {web}")
    print(f"Dashboard:     {web}/dashboard")
    if bot_username:
        print(f"Telegram bot:  https://t.me/{bot_username}")
    else:
        print("Telegram bot:  (TELEGRAM_BOT_TOKEN not set)")
    print(f"WhatsApp hook: {whatsapp_webhook}")
    print("  -> Twilio Console > Sandbox Settings > 'WHEN A MESSAGE COMES IN' (POST)")
    print("=" * 60)
    print()


if __name__ == "__main__":
    main()
