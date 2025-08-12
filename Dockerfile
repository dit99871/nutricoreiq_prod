# Этап сборки
FROM python:3.13-slim AS builder
RUN pip install --no-cache-dir poetry==1.8.3
WORKDIR /nutricoreiq
COPY pyproject.toml poetry.lock ./
RUN poetry export -f requirements.txt --output requirements.txt --without-hashes

# Финальный образ
FROM python:3.13-slim
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /nutricoreiq
COPY --from=builder /nutricoreiq/requirements.txt .
RUN pip install --no-cache-dir --root-user-action=ignore -r requirements.txt gunicorn
COPY . .

# Создаем пользователя, директории logs и certs с правильными правами
RUN useradd -m appuser && \
    mkdir -p /nutricoreiq/src/app/logs && \
    chown appuser:appuser /nutricoreiq/src/app/logs && \
    chmod 770 /nutricoreiq/src/app/logs && \
    chown -R appuser:appuser /nutricoreiq \
    chmod -R 500 /nutricoreiq/src/app/core/certs

COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

# Настройка PYTHONPATH
ENV PYTHONPATH=/nutricoreiq

CMD ["./entrypoint.sh"]