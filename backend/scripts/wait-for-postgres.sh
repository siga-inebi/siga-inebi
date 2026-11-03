#!/usr/bin/env sh
set -e

host="${1:-db}"
port="${2:-5432}"

until pg_isready -h "$host" -p "$port" -U "${DATABASE_USER:-siga_inebi}" -d "${DATABASE_NAME:-siga_inebi}"; do
  echo "Waiting for PostgreSQL at ${host}:${port}..."
  sleep 2
done
