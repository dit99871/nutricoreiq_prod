#!/bin/sh
set -e

# Создаем временный скрипт для хука
cat > /deploy-hook.sh << 'EOF'
#!/bin/sh
docker exec nginx nginx -s reload
EOF

# Делаем его исполняемым
chmod +x /deploy-hook.sh

# Запускаем certbot с хуком
exec certbot renew --quiet --deploy-hook /deploy-hook.sh