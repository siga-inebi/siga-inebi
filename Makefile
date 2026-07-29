SHELL := /bin/sh

.PHONY: help setup up down build restart logs ps shell-backend shell-frontend shell-db migrate migrations seed superuser test lint format check clean local-backend local-frontend

help:
	@printf "Available targets:\n"
	@printf "  make setup           Copy .env.example to .env if missing\n"
	@printf "  make up              Start Docker development stack\n"
	@printf "  make down            Stop Docker stack\n"
	@printf "  make build           Build Docker services\n"
	@printf "  make restart         Restart Docker stack\n"
	@printf "  make logs            Show Docker logs\n"
	@printf "  make ps              Show Docker services\n"
	@printf "  make shell-backend   Open backend shell\n"
	@printf "  make shell-frontend  Open frontend shell\n"
	@printf "  make shell-db        Open database shell\n"
	@printf "  make migrate         Run Django migrations\n"
	@printf "  make migrations      Create Django migrations\n"
	@printf "  make seed            Seed demo data\n"
	@printf "  make superuser       Create Django superuser\n"
	@printf "  make test            Run backend and frontend tests\n"
	@printf "  make lint            Run linters\n"
	@printf "  make format          Run formatters\n"
	@printf "  make check           Run validation checks\n"
	@printf "  make clean           Remove local caches and ask before DB reset\n"
	@printf "  make local-backend   Run Django locally\n"
	@printf "  make local-frontend  Run Vite locally\n"

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
	cd backend && ./.venv/bin/pytest
	cd frontend && npm run test -- --run

lint:
	cd backend && ./.venv/bin/ruff check .
	cd backend && ./.venv/bin/bandit -q -r apps config
	cd frontend && npm run lint

format:
	cd backend && ./.venv/bin/ruff format .
	cd frontend && npm run format

check:
	cd backend && ./.venv/bin/python manage.py check
	cd backend && ./.venv/bin/ruff check .
	cd frontend && npm run build

clean:
	@printf "This removes local caches. Continue? [y/N] " && read ans && [ "$$ans" = "y" ] || [ "$$ans" = "Y" ]
	find . -name "__pycache__" -type d -prune -exec rm -rf {} +
	find . -name ".pytest_cache" -type d -prune -exec rm -rf {} +
	rm -rf frontend/dist backend/.pytest_cache backend/htmlcov

local-backend:
	cd backend && ./.venv/bin/python manage.py runserver 0.0.0.0:8000

local-frontend:
	cd frontend && npm run dev
