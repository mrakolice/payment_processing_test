# syntax=docker/dockerfile:1.7
# Общий Dockerfile для api (FastAPI, app/web_app.py) и consumer (FastStream,
# app/consumer_app.py) — у них общий набор пакетов и общий код, поэтому собирается
# один образ. Контекст сборки — корень репозитория (здесь же лежат pyproject.toml
# и uv.lock). Конкретная команда запуска (uvicorn/faststream/alembic) задаётся
# в docker-compose.yml.

ARG PYTHON_VERSION=3.14

# ---------- builder: ставим uv с astral.sh и зависимости через uv sync ----------
FROM python:${PYTHON_VERSION}-slim AS builder

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN curl -LsSf "https://astral.sh/uv/install.sh" \
        | env UV_INSTALL_DIR=/usr/local/bin UV_NO_MODIFY_PATH=1 sh \
    && uv --version

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0 \
    UV_PROJECT_ENVIRONMENT=/app/.venv

WORKDIR /app

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    uv sync --frozen --no-dev --no-install-project

COPY . .
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

FROM python:${PYTHON_VERSION}-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:${PATH}"

RUN groupadd --system app && useradd --system --gid app --home-dir /app app

WORKDIR /app
COPY --from=builder --chown=app:app /app /app

USER app