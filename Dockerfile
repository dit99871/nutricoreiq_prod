# Базовый образ для сборки
FROM python:3.13-slim AS builder
RUN pip install --no-cache-dir poetry==1.8.3
WORKDIR /app
COPY pyproject.toml poetry.lock ./
# Экспортируем зависимости в requirements.txt для кэширования
RUN poetry export -f requirements.txt --output requirements.txt --without-hashes

# Финальный образ
FROM python:3.13-slim
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY --from=builder /app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
# Создаем не-root пользователя для безопасности
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser
CMD ["gunicorn", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "src.app.main:app", "--bind", "0.0.0.0:8000"]