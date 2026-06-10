# /Makefile
.PHONY: build up down clean fclean bup ngrok cloudflare telegram-setup links ps logs logs-backend logs-channels logs-frontend logs-db logs-redis test seed

build:
	docker compose build

up:
	docker compose up -d

down:
	docker compose down

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null; \
	find . -name "*.pyc" -delete 2>/dev/null; \

fclean: clean
	docker compose down -v

ngrok:
	@which ngrok > /dev/null || (echo "Error: ngrok not installed. Run: brew install ngrok" && exit 1)
	@pkill -f "ngrok http" 2>/dev/null; true
	@(ngrok http 3000 > /tmp/ngrok-moei.log 2>&1 &)
	@echo "Starting ngrok tunnel on port 3000..."
	@for i in $$(seq 1 30); do \
		curl -s http://localhost:4040/api/tunnels 2>/dev/null | grep -q '"public_url"' && break; \
		sleep 1; \
	done
	@python3 -c "\
import urllib.request, json, re, sys; \
data = json.loads(urllib.request.urlopen('http://localhost:4040/api/tunnels').read()); \
https = [t for t in data.get('tunnels',[]) if t['public_url'].startswith('https')]; \
sys.exit('Error: no HTTPS tunnel — is ngrok authenticated?') if not https else None; \
url = https[0]['public_url']; \
content = open('.env').read(); \
new = re.sub(r'PUBLIC_BASE_URL=.*', 'PUBLIC_BASE_URL=' + url, content) if 'PUBLIC_BASE_URL=' in content else content.rstrip() + '\nPUBLIC_BASE_URL=' + url + '\n'; \
open('.env','w').write(new); \
print('ngrok tunnel ready:', url)"

# Cloudflare quick tunnel for the Telegram webhook (separate from the ngrok
# tunnel used for PUBLIC_BASE_URL — Telegram needs its own stable HTTPS URL
# pointing at the channels service on port 8001).
cloudflare:
	@which cloudflared > /dev/null || (echo "Error: cloudflared not installed. Run: brew install cloudflared" && exit 1)
	@pkill -f "cloudflared tunnel" 2>/dev/null; true
	@rm -f /tmp/cloudflared-moei.log
	@(cloudflared tunnel --url http://localhost:8001 > /tmp/cloudflared-moei.log 2>&1 &)
	@echo "Starting Cloudflare tunnel on port 8001..."
	@for i in $$(seq 1 30); do \
		grep -qo 'https://[a-zA-Z0-9.-]*\.trycloudflare\.com' /tmp/cloudflared-moei.log && break; \
		sleep 1; \
	done; \
	url=$$(grep -o 'https://[a-zA-Z0-9.-]*\.trycloudflare\.com' /tmp/cloudflared-moei.log | head -1); \
	if [ -z "$$url" ]; then echo "Error: cloudflared tunnel did not start (see /tmp/cloudflared-moei.log)"; exit 1; fi; \
	python3 -c "\
import re; \
url = '$$url' + '/telegram/webhook'; \
content = open('.env').read(); \
new = re.sub(r'TELEGRAM_WEBHOOK_URL=.*', 'TELEGRAM_WEBHOOK_URL=' + url, content) if 'TELEGRAM_WEBHOOK_URL=' in content else content.rstrip() + '\nTELEGRAM_WEBHOOK_URL=' + url + '\n'; \
open('.env','w').write(new); \
print('Cloudflare tunnel ready:', url)"
	@docker compose up -d channels

telegram-setup:
	@echo "Waiting for channels service..."; \
	until curl -s http://localhost:8001/health > /dev/null 2>&1; do sleep 1; done; \
	curl -s -X POST http://localhost:8001/telegram/setup | python3 -m json.tool

bup: build up ngrok cloudflare telegram-setup links

links:
	@python3 scripts/print_links.py

ps:
	docker compose ps
	@echo "\n--- backend ---" && curl -s http://localhost:8000/health | python3 -m json.tool
	@echo "\n--- channels ---" && curl -s http://localhost:8001/health | python3 -m json.tool
	@echo "\n--- frontend ---" && curl -s -o /dev/null -w '{"frontend":"%{http_code}","url":"http://localhost:3000"}' http://localhost:3000 | python3 -m json.tool

logs:
	docker compose logs -f

logs-backend:
	docker compose logs -f backend

logs-channels:
	docker compose logs -f channels

logs-frontend:
	docker compose logs -f frontend

logs-db:
	docker compose logs -f db

logs-redis:
	docker compose logs -f redis

test:
	docker compose exec \
		-e TEST_BACKEND_URL=http://backend:8000 \
		-e TEST_CHANNELS_URL=http://channels:8001 \
		-e TEST_FRONTEND_URL=http://frontend:3000 \
		backend python -m pytest /tests/ -v

seed:
	python3 scripts/seed_demo.py
