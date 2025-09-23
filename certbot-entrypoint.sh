#!/bin/sh
set -x
set -e

echo "Starting certbot entrypoint script as user: $(whoami)"
mkdir -p /var/log/letsencrypt
echo "Current time: $(date)" >> /var/log/letsencrypt/certbot.log

# Проверяем доступ к Docker
ls -la /var/run/docker.sock >> /var/log/letsencrypt/certbot.log 2>&1
ls -la /var/run/ >> /var/log/letsencrypt/docker-check.log 2>&1

if ! docker ps > /dev/null 2>&1; then
  echo "Docker is not available or current user doesn't have permissions" | tee -a /var/log/letsencrypt/certbot.log
  echo "Trying with sudo..." | tee -a /var/log/letsencrypt/certbot.log
  if ! sudo docker ps > /dev/null 2>&1; then
    echo "Sudo docker also failed" | tee -a /var/log/letsencrypt/certbot.log
    exit 1
  fi
  DOCKER_CMD="sudo docker"
else
  DOCKER_CMD="docker"
fi

cat > /deploy-hook.sh << 'EOF'
#!/bin/sh
set -x
echo "Running deploy hook at $(date)" >> /var/log/letsencrypt/deploy-hook.log
if ! $DOCKER_CMD exec nginx nginx -s reload; then
  echo "Failed to reload nginx" >> /var/log/letsencrypt/deploy-hook.log
  exit 1
fi
echo "Nginx reloaded successfully" >> /var/log/letsencrypt/deploy-hook.log
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