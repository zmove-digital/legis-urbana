PY ?= python
VENV := .venv
BIN := $(VENV)/Scripts
WINBIN := $(VENV)/bin

.PHONY: help venv install dev run test lint fmt check seed docker clean

help:
	@echo "LegisUrb - comandos disponiveis:"
	@echo "  make install  instala dependencias (inclui extras de dev)"
	@echo "  make venv     cria o ambiente virtual .venv"
	@echo "  make dev      sobe a API com reload em http://127.0.0.1:8000"
	@echo "  make test     roda a suite de testes"
	@echo "  make lint     roda o ruff (check)"
	@echo "  make fmt      formata o codigo com ruff"
	@echo "  make check    lint + testes (o que a CI roda)"
	@echo "  make seed     recarrega a base legal do YAML no banco"
	@echo "  make docker   sobe a aplicacao com docker compose"
	@echo "  make clean    remove caches e artefatos"

venv:
	python -m venv $(VENV)

install:
	$(PY) -m pip install --upgrade pip
	$(PY) -m pip install -e ".[dev]"

dev:
	uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

run:
	uvicorn app.main:app --host 0.0.0.0 --port 8000

test:
	$(PY) -m pytest -q

lint:
	$(PY) -m ruff check .

fmt:
	$(PY) -m ruff format .

check: lint test

seed:
	$(PY) -c "from app.db import init_db, SessionLocal; from app.seed.loader import seed_all; init_db(); db = SessionLocal(); seed_all(db); db.close(); print('base legal recarregada')"

docker:
	docker compose up --build

clean:
	rm -rf .pytest_cache .ruff_cache **/__pycache__ *.egg-info
