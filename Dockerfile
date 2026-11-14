# syntax=docker/dockerfile:1
FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    BOARDGAME_APP_HOST=0.0.0.0 \
    BOARDGAME_APP_PORT=8088 \
    BOARDGAME_DB_PATH=/app/data/boardgames.sqlite3 \
    BOARDGAME_SEED_DEFAULTS=true

RUN groupadd --system appgroup \
    && useradd --system --gid appgroup --create-home appuser \
    && mkdir -p /app/data

COPY --chown=appuser:appgroup VERSION pyproject.toml README.md ./
COPY --chown=appuser:appgroup src/ ./src/

RUN chown -R appuser:appgroup /app/data

USER appuser

EXPOSE 8088

CMD ["python3", "-m", "src.api.app"]
