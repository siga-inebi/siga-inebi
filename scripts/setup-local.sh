#!/usr/bin/env bash
set -e

if [ ! -f .env ]; then
  cp .env.example .env
fi

python3 -m venv backend/.venv
backend/.venv/bin/pip install --upgrade pip
backend/.venv/bin/pip install -r backend/requirements/dev.txt

cd frontend
npm install
