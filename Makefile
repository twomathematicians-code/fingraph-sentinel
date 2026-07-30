.PHONY: install test lint run build clean

install:
	poetry install --with dev

test:
	poetry run pytest tests/ -v --tb=short --ignore=tests/test_graph.py

test-all:
	poetry run pytest tests/ -v --tb=short

lint:
	poetry run ruff check src/ tests/
	poetry run mypy src/ || true

format:
	poetry run black src/ tests/
	poetry run ruff check --fix src/ tests/

run:
	poetry run uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

build:
	docker build -t fingraph-sentinel .

up:
	docker-compose up --build

down:
	docker-compose down -v

seed:
	docker exec -i fingraph-neo4j cypher-shell -u neo4j -p fingraph-demo < data/seed_cypher.cql

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name '*.pyc' -delete 2>/dev/null || true
