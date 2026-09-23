FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# RNF-RES-001: el cliente de PostgreSQL debe compartir version MAYOR con el
# servidor de `compose.yml` (postgres:16). El paquete `postgresql-client` de
# Debian sigue su propia version -- hoy 17 -- y un pg_dump/pg_restore de otra
# mayor no puede respaldar ni restaurar contra ese servidor. Se fija la 16
# desde el repositorio oficial de PostgreSQL para que las herramientas de
# respaldo funcionen dentro del contenedor y no solo en el host de quien las
# escribio.
ARG POSTGRES_CLIENT_MAJOR=16
RUN sed -i 's|http://deb.debian.org|https://deb.debian.org|g' /etc/apt/sources.list.d/*.sources 2>/dev/null; \
    apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    ca-certificates \
    curl \
    gnupg \
    && install -d /usr/share/postgresql-common/pgdg \
    && curl -fsSL https://www.postgresql.org/media/keys/ACCC4CF8.asc \
       -o /usr/share/postgresql-common/pgdg/apt.postgresql.org.asc \
    && echo "deb [signed-by=/usr/share/postgresql-common/pgdg/apt.postgresql.org.asc] \
https://apt.postgresql.org/pub/repos/apt $(. /etc/os-release && echo $VERSION_CODENAME)-pgdg main" \
       > /etc/apt/sources.list.d/pgdg.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends "postgresql-client-${POSTGRES_CLIENT_MAJOR}" \
    && apt-get purge -y --auto-remove curl gnupg \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd --system app && useradd --system --gid app --create-home app

COPY requirements/base.txt requirements/dev.txt /tmp/requirements/
RUN pip install --upgrade pip && pip install -r /tmp/requirements/dev.txt

COPY . /app

RUN chmod +x /app/docker-entrypoint.sh && chown -R app:app /app

USER app

CMD ["/app/docker-entrypoint.sh"]
