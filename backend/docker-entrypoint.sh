#!/usr/bin/env sh
set -e

if [ "${DATABASE_ENGINE:-postgresql}" = "postgresql" ]; then
  /usr/bin/env sh /app/scripts/wait-for-postgres.sh "${DATABASE_HOST:-db}" "${DATABASE_PORT:-5432}"
fi

python manage.py migrate --noinput

if [ "${SEED_DEMO_DATA_ON_START:-false}" = "true" ]; then
  python manage.py seed_demo_data
fi

python manage.py runserver 0.0.0.0:${BACKEND_PORT:-8000}
