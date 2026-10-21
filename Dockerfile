# syntax=docker/dockerfile:1
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Dependencias do sistema (necessarias para build de wheels, quando houver)
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Camada de dependencias (aproveita cache entre builds)
COPY pyproject.toml README.md ./
RUN pip install --upgrade pip && pip install .

# Codigo e base legal
COPY app ./app
COPY data ./data

# Banco local (SQLite) em volume
ENV LEGIS_DB_URL="sqlite:////app/data/legis.db" \
    LEGIS_DATA_DIR="/app/data" \
    LEGIS_SEED_ON_STARTUP="1"

RUN mkdir -p /app/data && \
    useradd --create-home --uid 1000 legis && \
    chown -R legis:legis /app
USER legis

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8000/api/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
