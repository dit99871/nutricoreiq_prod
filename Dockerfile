# этап сборки
FROM python:3.13-slim AS builder
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /nutricoreiq
COPY pyproject.toml uv.lock ./

# устанавливаем только prod-зависимости в /nutricoreiq/.venv
RUN uv sync --frozen --no-dev --no-install-project

# финальный образ
FROM python:3.13-slim
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /nutricoreiq

# копируем готовый venv из builder
COPY --from=builder /nutricoreiq/.venv .venv

COPY . .

RUN useradd -m appuser && \
    mkdir -p /nutricoreiq/src/app/logs && \
    chown appuser:appuser /nutricoreiq/src/app/logs && \
    chmod 770 /nutricoreiq/src/app/logs && \
    chown -R appuser:appuser /nutricoreiq

COPY scripts/entrypoint.sh .
RUN chmod +x entrypoint.sh

ENV PYTHONPATH=/nutricoreiq
ENV PATH="/nutricoreiq/.venv/bin:$PATH"

CMD ["./entrypoint.sh"]