#!/bin/sh
set -x
set -e

echo "Starting certbot entrypoint script as user: $(whoami)"
mkdir -p /var/log/letsencrypt
echo "Current time: $(date)" >> /var/log/letsencrypt/certbot.log

# Создаем временный скрипт для хука
cat > /deploy-hook.sh << 'EOF'
#!/bin/sh
set -x
echo "Running deploy hook at $(date)" >> /var/log/letsencrypt/deploy-hook.log

# Создаем файл-триггер для перезагрузки nginx
touch /etc/letsencrypt/.need_reload
echo "Created reload trigger file" >> /var/log/letsencrypt/deploy-hook.log
EOF

chmod +x /deploy-hook.sh

echo "Running certbot renew..." >> /var/log/letsencrypt/certbot.log
certbot renew \
  --quiet \
  --deploy-hook /deploy-hook.sh \
  --logs-dir /var/log/letsencrypt \
  --work-dir /var/lib/letsencrypt \
  --config-dir /etc/letsencrypt \
  --max-log-backups 0

EXIT_CODE=$?
echo "Certbot exited with code: $EXIT_CODE" >> /var/log/letsencrypt/certbot.log
exit $EXIT_CODE