FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN sed -i 's|http://deb.debian.org|https://deb.debian.org|g' /etc/apt/sources.list.d/*.sources 2>/dev/null; \
    apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd --system app && useradd --system --gid app --create-home app

COPY requirements/base.txt requirements/dev.txt /tmp/requirements/
RUN pip install --upgrade pip && pip install -r /tmp/requirements/dev.txt

COPY . /app

RUN chmod +x /app/docker-entrypoint.sh && chown -R app:app /app

USER app

CMD ["/app/docker-entrypoint.sh"]
