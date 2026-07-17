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
RUN pip install --no-cache-dir '.[api]' \
    && pip install --no-cache-dir alembic

COPY apps/api ./apps/api
COPY apps/__init__.py ./apps/__init__.py
COPY migrations ./migrations
COPY alembic.ini ./alembic.ini

ENV PYTHONPATH=/app/src:/app

EXPOSE 8001

HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --retries=5 \
    CMD curl -f http://localhost:8001/api/v1/health/live || exit 1

CMD ["uvicorn", "apps.api.main:app", "--host", "0.0.0.0", "--port", "8001", "--workers", "2"]
