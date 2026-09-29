# Underdog — dev commands. Requires Python 3.12 at /opt/homebrew/bin/python3.12 (or PY env).

PY ?= /opt/homebrew/bin/python3.12
VENV := .venv
BIN := $(VENV)/bin
PIP := $(BIN)/pip
PYTHON := $(BIN)/python
PYTEST := $(BIN)/pytest
UVICORN := $(BIN)/uvicorn

FRONT := frontend

.PHONY: help venv install data sim seed eval dev backend frontend test lint clean docker-hindsight

help:
	@echo "make venv        Create .venv with Python 3.12"
	@echo "make install     Install project + dev deps into .venv"
	@echo "make data        Load real Amazon Reviews 2023 data (3 categories) + select brands + anonymise"
	@echo "make sim         Build simulator snapshots + outcomes from prepared data"
	@echo "make seed        Seed Hindsight bank with weeks 1..8, then clone to demo bank"
	@echo "make eval        Run memory on/off/oracle harness across seeds"
	@echo "make dev         Run backend + frontend"
	@echo "make backend     Run backend only"
	@echo "make frontend    Run frontend only"
	@echo "make test        Run pytest (excludes integration marker by default)"
	@echo "make lint        ruff + mypy"
	@echo "make docker-hindsight  Start Hindsight locally via docker-compose"

$(VENV)/bin/python:
	$(PY) -m venv $(VENV)
	$(PIP) install --upgrade pip

venv: $(VENV)/bin/python

install: venv
	$(PIP) install -e ".[dev]"

data:
	$(PYTHON) -m scripts.load_real_data
	$(PYTHON) -m scripts.select_brands
	$(PYTHON) -m scripts.anonymise

sim:
	$(PYTHON) -m scripts.build_sim

seed:
	$(PYTHON) -m scripts.seed_bank

eval:
	$(PYTHON) -m scripts.run_eval

backend:
	$(UVICORN) backend.app.main:app --reload --port 8000

frontend:
	cd $(FRONT) && npm run dev

dev:
	@echo "Starting backend (port 8000) and frontend (port 3000)..."
	@$(MAKE) -j2 backend frontend

test:
	$(PYTEST) -m "not integration"

test-integration:
	$(PYTEST) -m integration

lint:
	$(BIN)/ruff check backend scripts sim
	$(PYTHON) scripts/lint_no_em_dashes.py
	@out=$$(grep -R --include='*.py' "hindsight_client" backend/app | grep -v memory/service.py); \
	if [ -n "$$out" ]; then echo "LEAK: $$out"; exit 1; fi; \
	echo "grep: hindsight_client isolated to memory/service.py"
	@# Only the eval harness (which is *not* the agent) may read the hidden truth.
	@out=$$(grep -R --include='*.py' "ground_truth" backend/app | grep -v '/eval/'); \
	if [ -n "$$out" ]; then echo "LEAK: $$out"; exit 1; fi; \
	echo "grep: agent does not read ground_truth"

clean:
	rm -rf $(VENV) .pytest_cache .mypy_cache .ruff_cache

docker-hindsight:
	docker compose up -d hindsight
