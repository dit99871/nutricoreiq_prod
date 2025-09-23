#!/bin/sh
set -x  # Включаем отладочный вывод
set -e  # Выходим при ошибке

echo "Starting certbot entrypoint script..."

# Создаем каталог для логов, если его нет
mkdir -p /var/log/letsencrypt

# Записываем информацию о дате и времени
echo "Current time: $(date)" >> /var/log/letsencrypt/certbot.log

# Проверяем доступ к Docker
if ! docker ps > /dev/null 2>&1; then
  echo "Docker is not available or current user doesn't have permissions" | tee -a /var/log/letsencrypt/certbot.log
  exit 1
fi

# Создаем временный скрипт для хука
cat > /deploy-hook.sh << 'EOF'
#!/bin/sh
set -x
echo "Running deploy hook at $(date)" >> /var/log/letsencrypt/deploy-hook.log
if ! docker exec nginx nginx -s reload; then
  echo "Failed to reload nginx" >> /var/log/letsencrypt/deploy-hook.log
  exit 1
fi
echo "Nginx reloaded successfully" >> /var/log/letsencrypt/deploy-hook.log
EOF

# Делаем скрипт исполняемым
chmod +x /deploy-hook.sh

# Запускаем certbot с подробным логированием
echo "Running certbot renew..." >> /var/log/letsencrypt/certbot.log
certbot renew \
  --quiet \
  --deploy-hook /deploy-hook.sh \
  --logs-dir /var/log/letsencrypt \
  --work-dir /var/lib/letsencrypt \
  --config-dir /etc/letsencrypt \
  --max-log-backups 0

# Проверяем код выхода
EXIT_CODE=$?
echo "Certbot exited with code: $EXIT_CODE" >> /var/log/letsencrypt/certbot.log
exit $EXIT_CODE