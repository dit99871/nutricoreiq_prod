#!/bin/bash
set -e

echo "=== Начало деплоя NutriCoreIQ ==="
echo "DEPLOY_PATH: $DEPLOY_PATH"
echo "DOCKER_IMAGE: $DOCKER_IMAGE"
echo "DOCKER_REGISTRY: $DOCKER_REGISTRY"

# Валидация обязательных переменных
required_vars=("DEPLOY_PATH" "DOCKER_IMAGE" "DOCKER_REGISTRY")
for var in "${required_vars[@]}"; do
    if [[ -z "${!var}" ]]; then
        echo "ОШИБКА: Переменная $var не установлена"
        exit 1
    fi
done

# проверка доступных методов аутентификации
if [[ -z "$CI_JOB_TOKEN" && -z "$DEPLOY_TOKEN_USERNAME" ]]; then
    echo "ОШИБКА: Ни CI_JOB_TOKEN ни DEPLOY_TOKEN_USERNAME не доступны"
    echo "Установите хотя бы один метод аутентификации"
    exit 1
fi

# создание директории проекта
if ! mkdir -p "$DEPLOY_PATH"; then
    echo "ОШИБКА: Не удалось создать директорию $DEPLOY_PATH"
    exit 1
fi

# проверка доступа к Docker
if ! docker ps > /dev/null; then
    echo "ОШИБКА: Нет доступа к Docker"
    exit 1
fi

# копирование .env файла
if [[ -f "/etc/nutricoreiq/.env" ]]; then
    if ! cp /etc/nutricoreiq/.env "$DEPLOY_PATH/.env"; then
        echo "ОШИБКА: Не удалось скопировать .env файл"
        exit 1
    fi
    echo "✓ .env файл скопирован"
else
    echo "ПРЕДУПРЕЖДЕНИЕ: .env файл не найден в /etc/nutricoreiq/.env"
fi

# переход в директорию проекта
cd "$DEPLOY_PATH" || { echo "ОШИБКА: Не удалось перейти в $DEPLOY_PATH"; exit 1; }

echo "=== Выход из предыдущих Docker сессий ==="
docker logout "$DOCKER_REGISTRY" 2>/dev/null || true

echo "=== Логин в Docker Registry ==="
echo "Registry: $DOCKER_REGISTRY"

# проверяем доступные методы аутентификации
if [ -n "$CI_JOB_TOKEN" ]; then
    echo "Используем CI_JOB_TOKEN для аутентификации"
    if echo "$CI_JOB_TOKEN" | docker login -u gitlab-ci-token --password-stdin "$DOCKER_REGISTRY"; then
        echo "✓ Успешная авторизация через CI_JOB_TOKEN"
    else
        echo "ОШИБКА: Не удалось войти в Docker Registry с CI_JOB_TOKEN"
        echo "Пробуем Deploy Token..."
        
        if [ -n "$DEPLOY_TOKEN_USERNAME" ] && [ -n "$DEPLOY_TOKEN_PASSWORD" ]; then
            if echo "$DEPLOY_TOKEN_PASSWORD" | docker login -u "$DEPLOY_TOKEN_USERNAME" --password-stdin "$DOCKER_REGISTRY"; then
                echo "✓ Успешная авторизация через Deploy Token"
            else
                echo "ОШИБКА: Не удалось войти в Docker Registry"
                echo "Проверьте:"
                echo "1. CI_JOB_TOKEN имеет права на read_registry"
                echo "2. Deploy Token создан и активен"
                echo "3. Username и Password правильные"
                echo "4. Scope 'read_registry' включен"
                exit 1
            fi
        else
            echo "ОШИБКА: Deploy Token переменные не установлены"
            echo "CI_JOB_TOKEN не сработал, а Deploy Token отсутствует"
            exit 1
        fi
    fi
else
    echo "CI_JOB_TOKEN не установлен, пробуем Deploy Token..."
    
    if [ -n "$DEPLOY_TOKEN_USERNAME" ] && [ -n "$DEPLOY_TOKEN_PASSWORD" ]; then
        if echo "$DEPLOY_TOKEN_PASSWORD" | docker login -u "$DEPLOY_TOKEN_USERNAME" --password-stdin "$DOCKER_REGISTRY"; then
            echo "✓ Успешная авторизация через Deploy Token"
        else
            echo "ОШИБКА: Не удалось войти в Docker Registry"
            echo "Проверьте Deploy Token:"
            echo "1. Username и Password правильные"
            echo "2. Scope 'read_registry' включен"
            exit 1
        fi
    else
        echo "ОШИБКА: Ни CI_JOB_TOKEN ни Deploy Token не доступны"
        exit 1
    fi
fi

echo "=== Остановка старых контейнеров ==="
docker-compose -f docker-compose.prod.yml down || echo "ПРЕДУПРЕЖДЕНИЕ: старые контейнеры не найдены"

echo "=== Загрузка Docker образа: $DOCKER_IMAGE ==="
if ! docker pull "$DOCKER_IMAGE"; then
    echo "ОШИБКА: Не удалось загрузить образ $DOCKER_IMAGE"
    echo "Проверьте что образ существует в Container Registry"
    exit 1
fi

echo "✓ Образ успешно загружен"

echo "=== Запуск сервисов ==="
if ! docker-compose -f docker-compose.prod.yml up -d; then
    echo "ОШИБКА: Не удалось запустить сервисы"
    exit 1
fi

echo "=== Очистка старых образов ==="
docker image prune -f

echo "=== Ожидание запуска сервисов ==="
sleep 10

echo "=== Проверка статуса контейнеров ==="
docker ps -a

echo "=== Проверка health checks ==="
max_attempts=30
attempt=1

# проверяем здоровье только у критичных сервисов, от которых зависит работоспособность приложения.
critical_services=(db redis rabbitmq fastapi)

while [[ $attempt -le $max_attempts ]]; do
    echo "Попытка $attempt/$max_attempts"
    
    # проверяем статус всех сервисов
    unhealthy_services=$(
        for svc in "${critical_services[@]}"; do
            cid=$(docker-compose -f docker-compose.prod.yml ps -q "$svc" 2>/dev/null || true)
            if [[ -z "$cid" ]]; then
                echo "$svc missing"
                continue
            fi

            status=$(docker inspect --format='{{if .State.Health}}{{.State.Health.Status}}{{else}}no_healthcheck{{end}}' "$cid" 2>/dev/null || true)
            if [[ "$status" != "healthy" && "$status" != "no_healthcheck" ]]; then
                echo "$svc $status"
            fi
        done
    )
    
    if [[ -z "$unhealthy_services" ]]; then
        echo "✓ Все сервисы здоровы"
        break
    fi
    
    if [[ $attempt -eq $max_attempts ]]; then
        echo "ОШИБКА: Критичные сервисы не стали healthy за $max_attempts попыток"
        echo "Критичные сервисы: ${critical_services[*]}"
        echo "Нездоровые критичные сервисы (healthcheck):"
        echo "$unhealthy_services" | sed 's/^/ - /'

        # если есть реально упавшие контейнеры (Exited) — это считаем ошибкой деплоя.
        failed_services=$(docker ps -a --filter "status=exited" --format "{{.ID}}" || true)
        if [[ -n "$failed_services" ]]; then
            echo "ОШИБКА: Найдены упавшие контейнеры (Exited). Деплой прерван."
            for service in $failed_services; do
                echo "Логи контейнера $service:"
                docker logs "$service" --tail 50 || true
            done
            exit 1
        fi

        exit 1
    fi
    
    echo "Ожидание 10 секунд..."
    sleep 10
    ((attempt++))
done

echo "=== Проверка доступности приложения ==="
app_port=$(grep APP_CONFIG__RUN__PORT .env 2>/dev/null | cut -d'=' -f2 || echo "8080")
max_health_attempts=12
health_attempt=1

while [[ $health_attempt -le $max_health_attempts ]]; do
    if curl -f -s "http://localhost:$app_port/" > /dev/null 2>&1; then
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

echo "=== Выход из Docker Registry ==="
docker logout "$DOCKER_REGISTRY" || true

echo "=== Время завершения: $(date) ==="
