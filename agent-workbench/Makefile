setup:
	./setup.sh

connect:
	./setup.sh --connect

up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f --tail=100

health:
	curl -fsS http://localhost:8080/health

test:
	python -m pytest -q
