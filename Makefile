SHELL := /bin/sh

BACKEND_LOCAL_ENV = DATABASE_ENGINE=postgresql DATABASE_NAME=siga_inebi DATABASE_USER=siga_inebi DATABASE_PASSWORD=siga_inebi_dev_password DATABASE_HOST=127.0.0.1 DATABASE_PORT=5432
TEST_COMPOSE = docker compose -p siga_inebi_test -f compose.yml -f compose.test.yml

.PHONY: help setup up down build restart logs ps shell-backend shell-frontend shell-db migrate migrations seed superuser test lint format format-check check clean local-backend local-frontend lint-backend format-backend format-check-backend test-backend test-backend-unit test-backend-integration coverage-backend security-backend check-migrations test-frontend test-frontend-lint test-integration coverage security migrations-check ci-local

help:
	@printf "Available targets:\n"
	@printf "  make setup              Copy .env.example to .env if missing\n"
	@printf "  make up                 Start Docker development stack\n"
	@printf "  make down               Stop Docker stack\n"
	@printf "  make build              Build Docker services\n"
	@printf "  make restart            Restart Docker stack\n"
	@printf "  make logs               Show Docker logs\n"
	@printf "  make ps                 Show Docker services\n"
	@printf "  make shell-backend      Open backend shell\n"
	@printf "  make shell-frontend     Open frontend shell\n"
	@printf "  make shell-db           Open database shell\n"
	@printf "  make migrate            Run Django migrations\n"
	@printf "  make migrations         Create Django migrations\n"
	@printf "  make seed               Seed demo data\n"
	@printf "  make superuser          Create Django superuser\n"
	@printf "  make test               Run backend and frontend tests\n"
	@printf "  make test-backend       Run backend tests against PostgreSQL\n"
	@printf "  make test-frontend      Run frontend tests\n"
	@printf "  make lint               Run backend and frontend lint\n"
	@printf "  make format             Run formatters\n"
	@printf "  make format-check       Run formatter checks\n"
	@printf "  make coverage           Run coverage commands\n"
	@printf "  make security           Run security checks\n"
	@printf "  make migrations-check   Verify no missing migrations\n"
	@printf "  make ci-local           Reproduce CI-like Docker validation\n"
	@printf "  make clean              Remove local caches and ask before DB reset\n"
	@printf "  make local-backend      Run Django locally\n"
	@printf "  make local-frontend     Run Vite locally\n"

setup:
	@if [ ! -f .env ]; then cp .env.example .env; fi

up:
	docker compose up --build

down:
	docker compose down

build:
	docker compose build

restart:
	docker compose down
	docker compose up --build -d

logs:
	docker compose logs -f

ps:
	docker compose ps

shell-backend:
	docker compose exec backend sh

shell-frontend:
	docker compose exec frontend sh

shell-db:
	docker compose exec db sh

migrate:
	docker compose exec backend python manage.py migrate

migrations:
	docker compose exec backend python manage.py makemigrations

seed:
	docker compose exec backend python manage.py seed_demo_data

superuser:
	docker compose exec backend python manage.py createsuperuser

test:
	$(MAKE) test-backend
	$(MAKE) test-frontend

lint:
	$(MAKE) lint-backend
	$(MAKE) test-frontend-lint

format:
	$(MAKE) format-backend
	cd frontend && npm run format

format-check:
	$(MAKE) format-check-backend
	cd frontend && npm run format:check

check:
	$(MAKE) lint
	$(MAKE) format-check
	$(MAKE) test
	$(MAKE) coverage
	$(MAKE) build
	$(MAKE) migrations-check
	cd backend && $(BACKEND_LOCAL_ENV) ./.venv/bin/python manage.py check

clean:
	@printf "This removes local caches. Continue? [y/N] " && read ans && [ "$$ans" = "y" ] || [ "$$ans" = "Y" ]
	find . -name "__pycache__" -type d -prune -exec rm -rf {} +
	find . -name ".pytest_cache" -type d -prune -exec rm -rf {} +
	rm -rf frontend/dist frontend/coverage backend/.pytest_cache backend/htmlcov backend/coverage.xml

local-backend:
	cd backend && $(BACKEND_LOCAL_ENV) ./.venv/bin/python manage.py runserver 0.0.0.0:8000

local-frontend:
	cd frontend && npm run dev

lint-backend:
	cd backend && ./.venv/bin/ruff check .

format-backend:
	cd backend && ./.venv/bin/ruff format .

format-check-backend:
	cd backend && ./.venv/bin/ruff format --check .

test-backend:
	cd backend && $(BACKEND_LOCAL_ENV) ./.venv/bin/pytest

test-backend-unit:
	cd backend && $(BACKEND_LOCAL_ENV) ./.venv/bin/pytest -m unit

test-backend-integration:
	cd backend && $(BACKEND_LOCAL_ENV) ./.venv/bin/pytest -m "integration or api or permissions or migration"

coverage-backend:
	cd backend && $(BACKEND_LOCAL_ENV) ./.venv/bin/pytest

security-backend:
	cd backend && ./.venv/bin/bandit -q -r apps config
	cd backend && $(BACKEND_LOCAL_ENV) ./.venv/bin/pip-audit -r requirements/dev.txt --ignore-vuln PYSEC-2026-1845 --ignore-vuln GHSA-6v7p-g79w-8964 --ignore-vuln PYSEC-2026-1375 --ignore-vuln PYSEC-2026-1374 --ignore-vuln PYSEC-2026-2275 --ignore-vuln PYSEC-2026-142 --ignore-vuln PYSEC-2026-141

check-migrations:
	cd backend && $(BACKEND_LOCAL_ENV) ./.venv/bin/python manage.py makemigrations --check --dry-run

test-frontend:
	cd frontend && npm run test

test-frontend-lint:
	cd frontend && npm run lint

test-integration:
	$(MAKE) test-backend-integration

coverage:
	$(MAKE) coverage-backend
	cd frontend && npm run test:coverage

security:
	$(MAKE) security-backend

migrations-check:
	$(MAKE) check-migrations

ci-local:
	$(TEST_COMPOSE) build backend-test frontend
	$(TEST_COMPOSE) up -d db-test
	$(TEST_COMPOSE) run --rm backend-test
	$(TEST_COMPOSE) run --rm frontend npm run lint
	$(TEST_COMPOSE) run --rm frontend npm run test:coverage
	$(TEST_COMPOSE) run --rm frontend npm run build
	$(TEST_COMPOSE) run --rm backend-test sh -lc "ruff check . && ruff format --check . && python manage.py makemigrations --check --dry-run && bandit -q -r apps config && pip-audit -r requirements/dev.txt --ignore-vuln PYSEC-2026-1845 --ignore-vuln GHSA-6v7p-g79w-8964 --ignore-vuln PYSEC-2026-1375 --ignore-vuln PYSEC-2026-1374 --ignore-vuln PYSEC-2026-2275 --ignore-vuln PYSEC-2026-142 --ignore-vuln PYSEC-2026-141"
	$(TEST_COMPOSE) down -v --remove-orphans
