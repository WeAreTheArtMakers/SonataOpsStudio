.PHONY: up down logs seed listen-demo screenshots

up:
	docker compose up --build

down:
	docker compose down

logs:
	docker compose logs -f --tail=200

seed:
	curl -sS -X POST http://localhost:8000/admin/seed-demo

listen-demo:
	bash scripts/listen-demo.sh

screenshots:
	python3 scripts/capture_screenshots.py
