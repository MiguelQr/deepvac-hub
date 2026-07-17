FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
COPY src ./src
RUN pip install --no-cache-dir '.[web]' \
    && pip install --no-cache-dir alembic

COPY apps/web ./apps/web
COPY apps/__init__.py ./apps/__init__.py
COPY migrations ./migrations
COPY alembic.ini ./alembic.ini

ENV PYTHONPATH=/app/src:/app

EXPOSE 8002

HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --retries=5 \
    CMD curl -f http://localhost:8002/healthz || exit 1

CMD ["gunicorn", "--bind", "0.0.0.0:8002", "--workers", "2", "apps.web.app:app"]
