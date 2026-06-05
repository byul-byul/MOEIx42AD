# /Makefile
.PHONY: build up down clean fclean bup ngrok telegram-setup ps logs logs-backend logs-channels logs-frontend logs-db logs-redis

build:
	docker compose build

up:
	docker compose up -d

down:
	docker compose down

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null; \
	find . -name "*.pyc" -delete 2>/dev/null; \
	docker compose down --remove-orphans

fclean: clean
	docker compose down -v

ngrok:
	@which ngrok > /dev/null || (echo "Error: ngrok not installed. Run: brew install ngrok" && exit 1)
	@pkill -f "ngrok http 8001" 2>/dev/null; true
	@ngrok http 8001 > /tmp/ngrok-moei.log 2>&1 &
	@echo "Starting ngrok tunnel..."
	@sleep 2
	@python3 -c "\
import urllib.request, json, re, sys; \
data = json.loads(urllib.request.urlopen('http://localhost:4040/api/tunnels').read()); \
https = [t for t in data.get('tunnels',[]) if t['public_url'].startswith('https')]; \
sys.exit('Error: no HTTPS tunnel — is ngrok authenticated?') if not https else None; \
url = https[0]['public_url'] + '/telegram/webhook'; \
content = open('.env').read(); \
new = re.sub(r'TELEGRAM_WEBHOOK_URL=.*', 'TELEGRAM_WEBHOOK_URL=' + url, content) if 'TELEGRAM_WEBHOOK_URL=' in content else content.rstrip() + '\nTELEGRAM_WEBHOOK_URL=' + url + '\n'; \
open('.env','w').write(new); \
print('ngrok tunnel ready:', url)"

telegram-setup:
	@echo "Waiting for channels service..."; \
	until curl -s http://localhost:8001/health > /dev/null 2>&1; do sleep 1; done; \
	curl -s -X POST http://localhost:8001/telegram/setup | python3 -m json.tool

bup: ngrok build up telegram-setup

ps:
	docker compose ps
	@echo "\n--- backend ---" && curl -s http://localhost:8000/health | python3 -m json.tool
	@echo "\n--- channels ---" && curl -s http://localhost:8001/health | python3 -m json.tool

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
