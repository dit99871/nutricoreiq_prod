#!/bin/bash
set -e

# выполнение миграций
python -m alembic -c /nutricoreiq/alembic.ini upgrade head

echo "Настройка логов Nginx..."
LOG_DIR="/var/log/nginx"
APP_LOG_DIR="/nutricoreiq/src/app/logs"

# создаём директорию и файлы, если их нет
mkdir -p "$LOG_DIR"
touch "$LOG_DIR/access.log" "$LOG_DIR/error.log"

# права: appuser должен писать, Fail2Ban (root) должен читать
chown -R appuser:appuser "$LOG_DIR"
chmod -R 755 "$LOG_DIR"
chmod 644 "$LOG_DIR"/*.log

mkdir -p "$APP_LOG_DIR"
touch "$APP_LOG_DIR/app.log"
chown -R appuser:appuser "$APP_LOG_DIR"
chmod -R 755 "$APP_LOG_DIR"
chmod 644 "$APP_LOG_DIR"/*.log

# права на сертификаты (jwt)
CERTS_DIR="/nutricoreiq/src/app/core/certs"
echo "Настройка прав на сертификаты..."
mkdir -p "$CERTS_DIR"
chown -R appuser:appuser "$CERTS_DIR"
chmod 700 "$CERTS_DIR"

for file in jwt-private.pem jwt-public.pem; do
  if [ -f "$CERTS_DIR/$file" ]; then
    chown appuser:appuser "$CERTS_DIR/$file"
    chmod 600 "$CERTS_DIR/$file"
  fi
done

# запуск гуникорна от имени appuser
echo "Запуск Gunicorn..."
exec runuser -u appuser -- gunicorn \
  -w 4 \
  -k uvicorn.workers.UvicornWorker \
  src.app.main:app \
  --bind 0.0.0.0:8080 \
  --max-requests 1000 \
  --max-requests-jitter 200 \
  --timeout 60 \
  --graceful-timeout 30 \
  --keep-alive 5 \
  --disable-redirect-access-to-syslog \
  --access-logfile /dev/null \
  --error-logfile - \
  --log-level warning \
  --capture-output