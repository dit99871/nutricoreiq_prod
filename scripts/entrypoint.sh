#!/bin/bash
set -e
# Выполнение миграций
python -m alembic -c /nutricoreiq/alembic.ini upgrade head
# Проверка и исправление прав для логов
echo "Checking log directory permissions:"
ls -ld /nutricoreiq/src/app/logs
echo "Current user before changes:"
id
chown 1000:1000 /nutricoreiq/src/app/logs
chmod 755 /nutricoreiq/src/app/logs
touch /nutricoreiq/src/app/logs/app.log
chown 1000:1000 /nutricoreiq/src/app/logs/app.log
chmod 644 /nutricoreiq/src/app/logs/app.log
echo "Updated log directory permissions:"
ls -ld /nutricoreiq/src/app/logs
ls -l /nutricoreiq/src/app/logs
# Проверка и исправление прав для сертификатов
echo "Checking certs directory permissions:"
ls -ld /nutricoreiq/src/app/core/certs
chown 1000:1000 /nutricoreiq/src/app/core/certs
chmod 700 /nutricoreiq/src/app/core/certs
if [ -f /nutricoreiq/src/app/core/certs/jwt-private.pem ]; then
  chown 1000:1000 /nutricoreiq/src/app/core/certs/jwt-private.pem
  chmod 600 /nutricoreiq/src/app/core/certs/jwt-private.pem
fi
if [ -f /nutricoreiq/src/app/core/certs/jwt-public.pem ]; then
  chown 1000:1000 /nutricoreiq/src/app/core/certs/jwt-public.pem
  chmod 600 /nutricoreiq/src/app/core/certs/jwt-public.pem
fi
echo "Updated certs directory permissions:"
ls -ld /nutricoreiq/src/app/core/certs
ls -l /nutricoreiq/src/app/core/certs
# Переключаемся на appuser и запускаем Gunicorn
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
  --access-logfile /dev/null \
  --error-logfile - \
  --log-level error
