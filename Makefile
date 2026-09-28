.PHONY: up down test lint format seed ingest eval consolidate install clean

install:
	uv pip install -e ".[dev]"

up:
	docker compose up -d db redis
	@echo "Waiting for PostgreSQL and Redis to be healthy..."
	@until docker compose ps db | grep -q "healthy"; do sleep 1; done
	@until docker compose ps redis | grep -q "healthy"; do sleep 1; done
	@echo "Infrastructure is up and healthy."

down:
	docker compose down

test:
	pytest tests/

lint:
	ruff check .
	ruff format --check .

format:
	ruff format .
	ruff check --fix .

seed:
	python -m app.cli seed

ingest:
	python -m app.cli ingest data/seed

eval:
	python -m app.cli eval

consolidate:
	python -m app.cli consolidate

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name .pytest_cache -exec rm -rf {} +
	find . -type d -name .ruff_cache -exec rm -rf {} +

demo:
	python -m app.cli demo

dashboard:
	python -m app.cli dashboard
