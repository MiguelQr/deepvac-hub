# Used for one-off/dev tasks: alembic migrations, admin creation, seeding,
# and running the test suite / lint / type-check against the compose
# network's postgres. Not part of the production runtime topology.
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
RUN pip install --no-cache-dir '.[api,web,dev]' \
    && pip install --no-cache-dir alembic

COPY apps ./apps
COPY migrations ./migrations
COPY scripts ./scripts
COPY tests ./tests
COPY alembic.ini ./alembic.ini

ENV PYTHONPATH=/app/src:/app

CMD ["sleep", "infinity"]
