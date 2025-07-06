#!/bin/bash
# Ожидание готовности PostgreSQL
until pg_isready -h db -p 5432 -U "${POSTGRES_USER:-user}" -d nutricoreiq; do
  echo "Waiting for PostgreSQL to be ready..."
  sleep 2
done
# Ожидание готовности Redis
until redis-cli -h redis -p 6379 ping; do
  echo "Waiting for Redis to be ready..."
  sleep 2
done
# Выполнение миграций
alembic upgrade head
# Проверка и исправление прав для логов
echo "Checking log directory permissions:"
ls -ld /nutricoreiq/src/app/logs
echo "Current user before changes:"
id
chown 1000:1000 /nutricoreiq/src/app/logs
chmod 770 /nutricoreiq/src/app/logs
touch /nutricoreiq/src/app/logs/app.log
chown 1000:1000 /nutricoreiq/src/app/logs/app.log
chmod 660 /nutricoreiq/src/app/logs/app.log
echo "Updated log directory permissions:"
ls -ld /nutricoreiq/src/app/logs
ls -l /nutricoreiq/src/app/logs
# Проверка и исправление прав для сертификатов
echo "Checking certs directory permissions:"
ls -ld /nutricoreiq/src/app/utils/certs
chown 1000:1000 /nutricoreiq/src/app/utils/certs
chmod 700 /nutricoreiq/src/app/utils/certs
if [ -f /nutricoreiq/src/app/utils/certs/jwt-private.pem ]; then
  chown 1000:1000 /nutricoreiq/src/app/utils/certs/jwt-private.pem
  chmod 600 /nutricoreiq/src/app/utils/certs/jwt-private.pem
fi
if [ -f /nutricoreiq/src/app/utils/certs/jwt-public.pem ]; then
  chown 1000:1000 /nutricoreiq/src/app/utils/certs/jwt-public.pem
  chmod 600 /nutricoreiq/src/app/utils/certs/jwt-public.pem
fi
echo "Updated certs directory permissions:"
ls -ld /nutricoreiq/src/app/utils/certs
ls -l /nutricoreiq/src/app/utils/certs
# Переключаемся на appuser и запускаем Gunicorn
exec runuser -u appuser -- gunicorn -w 4 -k uvicorn.workers.UvicornWorker src.app.main:app --bind 0.0.0.0:8080
