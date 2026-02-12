#!/bin/bash
set -e

echo "=== Начало деплоя NutriCoreIQ ==="
echo "DEPLOY_PATH: $DEPLOY_PATH"
echo "DOCKER_IMAGE: $DOCKER_IMAGE"
echo "DOCKER_REGISTRY: $DOCKER_REGISTRY"

# Валидация обязательных переменных
required_vars=("DEPLOY_PATH" "DOCKER_IMAGE" "DOCKER_REGISTRY" "DEPLOY_TOKEN_USERNAME" "DEPLOY_TOKEN_PASSWORD")
for var in "${required_vars[@]}"; do
    if [[ -z "${!var}" ]]; then
        echo "ОШИБКА: Переменная $var не установлена"
        exit 1
    fi
done

# Создание директории проекта
if ! mkdir -p "$DEPLOY_PATH"; then
    echo "ОШИБКА: Не удалось создать директорию $DEPLOY_PATH"
    exit 1
fi

# Проверка доступа к Docker
if ! docker ps > /dev/null; then
    echo "ОШИБКА: Нет доступа к Docker"
    exit 1
fi

# Копирование .env файла
if [[ -f "/etc/nutricoreiq/.env" ]]; then
    if ! cp /etc/nutricoreiq/.env "$DEPLOY_PATH/.env"; then
        echo "ОШИБКА: Не удалось скопировать .env файл"
        exit 1
    fi
    echo "✓ .env файл скопирован"
else
    echo "ПРЕДУПРЕЖДЕНИЕ: .env файл не найден в /etc/nutricoreiq/.env"
fi

# Переход в директорию проекта
cd "$DEPLOY_PATH" || { echo "ОШИБКА: Не удалось перейти в $DEPLOY_PATH"; exit 1; }

# Логаут из старых сессий
echo "=== Выход из предыдущих Docker сессий ==="
docker logout "$DOCKER_REGISTRY" 2>/dev/null || true

# Логин в Docker Registry
echo "=== Логин в Docker Registry ==="
echo "Registry: $DOCKER_REGISTRY"
echo "Username: $DEPLOY_TOKEN_USERNAME"

if ! echo "$DEPLOY_TOKEN_PASSWORD" | docker login -u "$DEPLOY_TOKEN_USERNAME" --password-stdin "$DOCKER_REGISTRY"; then
    echo "ОШИБКА: Не удалось войти в Docker Registry"
    echo "Проверьте:"
    echo "1. Deploy Token создан и активен"
    echo "2. Username и Password правильные"
    echo "3. Scope 'read_registry' включен"
    exit 1
fi

echo "✓ Успешная авторизация в registry"

# Остановка старых контейнеров
echo "=== Остановка старых контейнеров ==="
docker-compose -f docker-compose.prod.yml down || echo "ПРЕДУПРЕЖДЕНИЕ: старые контейнеры не найдены"

# Загрузка нового Docker-образа
echo "=== Загрузка Docker образа: $DOCKER_IMAGE ==="
if ! docker pull "$DOCKER_IMAGE"; then
    echo "ОШИБКА: Не удалось загрузить образ $DOCKER_IMAGE"
    echo "Проверьте что образ существует в Container Registry"
    exit 1
fi

echo "✓ Образ успешно загружен"

# Запуск сервисов
echo "=== Запуск сервисов ==="
if ! docker-compose -f docker-compose.prod.yml up -d; then
    echo "ОШИБКА: Не удалось запустить сервисы"
    exit 1
fi

# Очистка неиспользуемых образов
echo "=== Очистка старых образов ==="
docker image prune -f

# Ожидание запуска сервисов
echo "=== Ожидание запуска сервисов ==="
sleep 10

# Проверка статуса контейнеров
echo "=== Проверка статуса контейнеров ==="
docker ps -a

# Проверка health checks
echo "=== Проверка health checks ==="
max_attempts=30
attempt=1

while [[ $attempt -le $max_attempts ]]; do
    echo "Попытка $attempt/$max_attempts"
    
    # Проверяем статус всех сервисов
    unhealthy_services=$(docker ps --services --filter "status=running" | xargs -I {} docker-compose -f docker-compose.prod.yml ps -q {} | xargs -I {} docker inspect --format='{{.State.Health.Status}}' {} 2>/dev/null | grep -v "healthy" || true)
    
    if [[ -z "$unhealthy_services" ]]; then
        echo "✓ Все сервисы здоровы"
        break
    fi
    
    if [[ $attempt -eq $max_attempts ]]; then
        echo "ОШИБКА: Сервисы не стали здоровыми за $max_attempts попыток"
        echo "Нездоровые сервисы:"
        docker ps -a | grep -E "(Up.*unhealthy|Exited)"
        
        # Показываем логи упавших сервисов
        failed_services=$(docker ps -a | grep Exited | awk '{print $1}' || true)
        for service in $failed_services; do
            echo "Логи сервиса $service:"
            docker logs "$service" --tail 50 || true
        done
        exit 1
    fi
    
    echo "Ожидание 10 секунд..."
    sleep 10
    ((attempt++))
done

# Проверка доступности основного приложения
echo "=== Проверка доступности приложения ==="
app_port=$(grep APP_CONFIG__RUN__PORT .env 2>/dev/null | cut -d'=' -f2 || echo "8080")
max_health_attempts=12
health_attempt=1

while [[ $health_attempt -le $max_health_attempts ]]; do
    if curl -f -s "http://localhost:$app_port/health" > /dev/null 2>&1; then
        echo "✓ Приложение доступно и отвечает на health check"
        break
    fi
    
    if [[ $health_attempt -eq $max_health_attempts ]]; then
        echo "ОШИБКА: Приложение не отвечает на health check"
        echo "Проверка логов fastapi:"
        docker logs web_app --tail 50 || true
        exit 1
    fi
    
    echo "Ожидание ответа от приложения... ($health_attempt/$max_health_attempts)"
    sleep 5
    ((health_attempt++))
done

echo "=== Деплой успешно завершен ==="
echo "Приложение доступно на порту: $app_port"

# Выход из Docker Registry
echo "=== Выход из Docker Registry ==="
docker logout "$DOCKER_REGISTRY" || true

echo "=== Время завершения: $(date) ==="
