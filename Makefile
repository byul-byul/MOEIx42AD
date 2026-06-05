# /Makefile
.PHONY: build up down clean fclean bup ps logs logs-backend logs-channels logs-db logs-redis

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

bup: build up

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

logs-db:
	docker compose logs -f db

logs-redis:
	docker compose logs -f redis
