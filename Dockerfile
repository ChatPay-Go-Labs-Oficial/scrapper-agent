# Dockerfile multi-stage para API e Worker
FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml uv.lock ./

RUN pip install uv \
    && uv sync --frozen

COPY . .

RUN useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app


FROM base AS api

USER app

EXPOSE 8000

CMD ["uv", "run", "python", "main.py"]


FROM base AS worker

USER app

CMD ["uv", "run", "python", "-m", "worker.ingestion_worker"]
