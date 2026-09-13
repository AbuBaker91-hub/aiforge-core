.PHONY: setup test lint

setup:
	python -m venv .venv || true
	. .venv/bin/activate && pip install -e ".[dev]"
	docker compose up -d

test:
	pytest

lint:
	ruff check .
