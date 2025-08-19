# Анализ развертывания - NutriCoreIQ

## Общая оценка: 8/10

### ✅ Отличные решения развертывания

#### 1. Контейнеризация с Docker
```dockerfile
# Dockerfile - хорошо структурированный
FROM python:3.13-slim AS builder  # Multi-stage build
RUN pip install --no-cache-dir poetry==1.8.3
WORKDIR /nutricoreiq
COPY pyproject.toml poetry.lock ./
RUN poetry export -f requirements.txt --output requirements.txt --without-hashes

# Production образ оптимизирован
FROM python:3.13-slim
RUN apt-get update && apt-get install -y --no-install-recommends libpq-dev
# Создание непривилегированного пользователя
RUN useradd -m appuser && chown -R appuser:appuser /nutricoreiq
```

#### 2. Production-ready Docker Compose
```yaml
# docker-compose.prod.yml - полноценный production stack
services:
  db:           # PostgreSQL с persistence
  redis:        # Кэширование и сессии
  rabbitmq:     # Очереди задач
  fastapi:      # Основное приложение
  taskiq_worker: # Воркеры для фоновых задач
  nginx:        # Reverse proxy
  prometheus:   # Метрики
  grafana:      # Дашборды
  loki:         # Логирование
  promtail:     # Сбор логов
```

#### 3. Мониторинг и наблюдаемость
```yaml
# Полный monitoring stack:
- Prometheus    # Сбор метрик
- Grafana      # Визуализация
- Loki         # Централизованное логирование
- Promtail     # Агент сбора логов
- Node Exporter # Системные метрики
- Redis Exporter # Метрики Redis
- Postgres Exporter # Метрики БД
```

#### 4. Health Checks
```yaml
# Правильные health checks для всех сервисов
db:
  healthcheck:
    test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
    interval: 5s
    timeout: 5s
    retries: 5

fastapi:
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:${APP_CONFIG__RUN__PORT}"]
    interval: 5s
    timeout: 5s
    retries: 5
```

#### 5. Безопасность развертывания
```yaml
# Хорошие практики безопасности:
- Непривилегированный пользователь в контейнере
- Bind только на localhost для служебных портов
- Использование secrets через переменные окружения
- Изоляция сети через docker network
```

### ⚠️ Проблемы развертывания

#### 1. Отсутствие CI/CD пайплайна
```bash
# ОТСУТСТВУЕТ:
- GitHub Actions / GitLab CI конфигурация
- Автоматические тесты перед деплоем
- Автоматический build и push образов
- Deployment automation
- Rollback механизмы
```

#### 2. Недостаток production конфигурации

**Отсутствие SSL/TLS настроек**
```nginx
# ПРОБЛЕМА: Nginx конфигурация не показана
# НУЖНО ДОБАВИТЬ: nginx.conf с SSL
server {
    listen 443 ssl http2;
    server_name nutricoreiq.ru;

    ssl_certificate /etc/letsencrypt/live/nutricoreiq.ru/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/nutricoreiq.ru/privkey.pem;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options DENY always;
    add_header X-Content-Type-Options nosniff always;
}
```

**Отсутствие backup стратегии**
```bash
# ОТСУТСТВУЕТ:
- Автоматический backup БД
- Backup конфигураций
- Disaster recovery план
- Восстановление данных
```

#### 3. Scaling и производительность

**Отсутствие горизонтального масштабирования**
```yaml
# ПРОБЛЕМА: Один экземпляр FastAPI
fastapi:
  # Нет replicas или load balancing

# РЕШЕНИЕ: Docker Swarm или Kubernetes
fastapi:
  deploy:
    replicas: 3
    update_config:
      parallelism: 1
      delay: 10s
    restart_policy:
      condition: on-failure
```

**Недостаток ресурсных ограничений**
```yaml
# ДОБАВИТЬ: Resource limits
services:
  fastapi:
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 512M
        reservations:
          cpus: '0.5'
          memory: 256M
```

#### 4. Отсутствие staging окружения
```bash
# НУЖНО ДОБАВИТЬ:
- docker-compose.staging.yml
- Отдельные конфигурации для staging
- Automated deployment в staging
- Testing на staging перед production
```

#### 5. Недостающая документация деплоя
```markdown
# ОТСУТСТВУЕТ:
- Инструкции по первоначальной настройке
- Процедуры обновления
- Troubleshooting guide
- Monitoring setup
- Backup/restore процедуры
```

### 🔧 Рекомендуемые улучшения

#### 1. Создать CI/CD пайплайн
```yaml
# .github/workflows/deploy.yml
name: Deploy to Production

on:
  push:
    branches: [main]
    tags: ['v*']

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run tests
        run: |
          docker-compose -f docker-compose.test.yml up --build --abort-on-container-exit

  build:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Build and push Docker images
        env:
          DOCKER_BUILDKIT: 1
        run: |
          echo ${{ secrets.DOCKER_PASSWORD }} | docker login -u ${{ secrets.DOCKER_USERNAME }} --password-stdin
          docker build -t nutricoreiq/app:${{ github.sha }} .
          docker build -t nutricoreiq/nginx:${{ github.sha }} -f Dockerfile.nginx .
          docker push nutricoreiq/app:${{ github.sha }}
          docker push nutricoreiq/nginx:${{ github.sha }}

  deploy:
    needs: build
    runs-on: self-hosted  # Production server
    if: github.ref == 'refs/heads/main'
    steps:
      - name: Deploy to production
        run: |
          docker-compose -f docker-compose.prod.yml pull
          docker-compose -f docker-compose.prod.yml up -d
          docker system prune -f
```

#### 2. Добавить Kubernetes манифесты
```yaml
# k8s/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: nutricoreiq

---
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nutricoreiq-app
  namespace: nutricoreiq
spec:
  replicas: 3
  selector:
    matchLabels:
      app: nutricoreiq-app
  template:
    metadata:
      labels:
        app: nutricoreiq-app
    spec:
      containers:
      - name: app
        image: nutricoreiq/app:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: nutricoreiq-secrets
              key: database-url
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 500m
            memory: 512Mi

---
# k8s/service.yaml
apiVersion: v1
kind: Service
metadata:
  name: nutricoreiq-service
  namespace: nutricoreiq
spec:
  selector:
    app: nutricoreiq-app
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
  type: ClusterIP

---
# k8s/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: nutricoreiq-ingress
  namespace: nutricoreiq
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
spec:
  tls:
  - hosts:
    - nutricoreiq.ru
    secretName: nutricoreiq-tls
  rules:
  - host: nutricoreiq.ru
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: nutricoreiq-service
            port:
              number: 80
```

#### 3. Создать backup стратегию
```bash
# scripts/backup.sh
#!/bin/bash

# Backup PostgreSQL
BACKUP_DIR="/backups/$(date +%Y-%m-%d)"
mkdir -p $BACKUP_DIR

docker exec postgre pg_dump -U $POSTGRES_USER $POSTGRES_DB | gzip > $BACKUP_DIR/database.sql.gz

# Backup uploads/files
tar -czf $BACKUP_DIR/files.tar.gz /app/uploads/

# Backup configurations
cp -r /app/config $BACKUP_DIR/

# Upload to S3 (или другое облачное хранилище)
aws s3 sync $BACKUP_DIR s3://nutricoreiq-backups/$(date +%Y-%m-%d)/

# Cleanup old backups (оставить последние 30 дней)
find /backups -type d -mtime +30 -exec rm -rf {} \;

echo "Backup completed: $BACKUP_DIR"
```

```yaml
# cron job для автоматического backup
# /etc/crontab
0 2 * * * root /app/scripts/backup.sh >> /var/log/backup.log 2>&1
```

#### 4. Добавить мониторинг приложения
```python
# monitoring/alerts.py
from prometheus_client import Counter, Histogram, Gauge

# Application metrics
request_count = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'status'])
request_duration = Histogram('http_request_duration_seconds', 'HTTP request duration')
active_users = Gauge('active_users_total', 'Currently active users')
database_connections = Gauge('database_connections_active', 'Active database connections')

# Business metrics
user_registrations = Counter('user_registrations_total', 'Total user registrations')
product_searches = Counter('product_searches_total', 'Total product searches')
failed_logins = Counter('failed_logins_total', 'Failed login attempts')
```

```yaml
# prometheus/alerts.yml
groups:
  - name: nutricoreiq.rules
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.1
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value }} errors per second"

      - alert: DatabaseConnectionsHigh
        expr: database_connections_active > 40
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "High database connection usage"

      - alert: ApplicationDown
        expr: up{job="nutricoreiq"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "NutriCoreIQ application is down"
```

#### 5. Создать staging окружение
```yaml
# docker-compose.staging.yml
version: "3.9"

services:
  # Упрощенная версия production setup для staging
  db-staging:
    image: postgres:17
    environment:
      POSTGRES_DB: nutricoreiq_staging
      POSTGRES_USER: staging_user
      POSTGRES_PASSWORD: staging_pass
    volumes:
      - staging_postgres_data:/var/lib/postgresql/data
    ports:
      - "127.0.0.1:5433:5432"

  redis-staging:
    image: redis:latest
    ports:
      - "127.0.0.1:6380:6379"
    volumes:
      - staging_redis_data:/data

  fastapi-staging:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "127.0.0.1:8001:8000"
    environment:
      - APP_CONFIG__DB__URL=postgresql+asyncpg://staging_user:staging_pass@db-staging:5432/nutricoreiq_staging
      - APP_CONFIG__REDIS__URL=redis://redis-staging:6379
      - APP_CONFIG__DEBUG=true
    depends_on:
      - db-staging
      - redis-staging

volumes:
  staging_postgres_data:
  staging_redis_data:
```

### 🚀 Инструменты для деплоя

#### 1. Terraform для инфраструктуры
```hcl
# terraform/main.tf
provider "aws" {
  region = "eu-west-1"
}

# VPC и сетевая инфраструктура
resource "aws_vpc" "nutricoreiq" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name = "nutricoreiq-vpc"
  }
}

# ECS Cluster для контейнеров
resource "aws_ecs_cluster" "nutricoreiq" {
  name = "nutricoreiq-cluster"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

# RDS для PostgreSQL
resource "aws_db_instance" "nutricoreiq" {
  identifier     = "nutricoreiq-db"
  engine         = "postgres"
  engine_version = "17"
  instance_class = "db.t3.micro"

  allocated_storage     = 20
  max_allocated_storage = 100
  storage_encrypted     = true

  db_name  = "nutricoreiq"
  username = var.db_username
  password = var.db_password

  vpc_security_group_ids = [aws_security_group.rds.id]
  db_subnet_group_name   = aws_db_subnet_group.nutricoreiq.name

  backup_retention_period = 7
  backup_window          = "03:00-04:00"
  maintenance_window     = "sun:04:00-sun:05:00"

  skip_final_snapshot = false
  final_snapshot_identifier = "nutricoreiq-final-snapshot"

  tags = {
    Name = "nutricoreiq-database"
  }
}

# ElastiCache для Redis
resource "aws_elasticache_subnet_group" "nutricoreiq" {
  name       = "nutricoreiq-cache-subnet"
  subnet_ids = aws_subnet.private[*].id
}

resource "aws_elasticache_cluster" "nutricoreiq" {
  cluster_id           = "nutricoreiq-redis"
  engine               = "redis"
  node_type            = "cache.t3.micro"
  num_cache_nodes      = 1
  parameter_group_name = "default.redis7"
  port                 = 6379
  subnet_group_name    = aws_elasticache_subnet_group.nutricoreiq.name
  security_group_ids   = [aws_security_group.redis.id]
}
```

#### 2. Ansible для конфигурации
```yaml
# ansible/playbook.yml
---
- name: Deploy NutriCoreIQ
  hosts: production
  become: yes
  vars:
    app_dir: /opt/nutricoreiq
    docker_compose_version: "2.20.0"

  tasks:
    - name: Install Docker
      apt:
        name: docker.io
        state: present
        update_cache: yes

    - name: Install Docker Compose
      pip:
        name: docker-compose
        version: "{{ docker_compose_version }}"

    - name: Create app directory
      file:
        path: "{{ app_dir }}"
        state: directory
        owner: www-data
        group: www-data

    - name: Copy docker-compose.prod.yml
      template:
        src: docker-compose.prod.yml.j2
        dest: "{{ app_dir }}/docker-compose.prod.yml"
      notify: restart services

    - name: Copy environment file
      template:
        src: .env.j2
        dest: "{{ app_dir }}/.env"
        mode: '0600'
      notify: restart services

    - name: Start services
      docker_compose:
        project_src: "{{ app_dir }}"
        file: docker-compose.prod.yml
        state: present

  handlers:
    - name: restart services
      docker_compose:
        project_src: "{{ app_dir }}"
        file: docker-compose.prod.yml
        state: present
        pull: yes
```

### 📊 Deployment metrics

#### Текущее состояние
- **Контейнеризация**: ✅ Полная
- **Orchestration**: ⚠️ Docker Compose только
- **CI/CD**: ❌ Отсутствует
- **Monitoring**: ✅ Полный stack
- **Backup**: ❌ Не настроен
- **Security**: ⚠️ Базовая
- **Scaling**: ❌ Manual только

#### Целевые показатели
- **Deployment time**: < 5 минут
- **Zero-downtime deployments**: ✅
- **Rollback time**: < 2 минуты
- **Monitoring coverage**: 95%
- **Backup RTO**: < 1 час
- **High availability**: 99.9% uptime

### 🎯 Roadmap развертывания

#### Краткосрочный (1-2 недели)
- Настроить CI/CD пайплайн
- Добавить backup скрипты
- Создать staging окружение
- Написать deployment документацию

#### Среднесрочный (1 месяц)
- Мигрировать на Kubernetes
- Настроить автоскейлинг
- Добавить blue-green deployment
- Реализовать disaster recovery

#### Долгосрочный (3 месяца)
- Multi-region deployment
- CDN интеграция
- Advanced monitoring и alerting
- Compliance и security hardening

### 🔐 Security checklist для деплоя

#### Контейнеры ✅/❌
- ✅ Non-root пользователь
- ✅ Minimal base image
- ❌ Image scanning
- ❌ Runtime security
- ✅ Secret management

#### Сеть ✅/❌
- ✅ Network isolation
- ❌ SSL/TLS everywhere
- ❌ WAF (Web Application Firewall)
- ✅ Port restrictions
- ❌ VPN access

#### Данные ✅/❌
- ⚠️ Encryption at rest
- ❌ Encryption in transit
- ❌ Regular security updates
- ❌ Vulnerability scanning
- ✅ Access controls

**Итог**: Проект имеет отличную основу для развертывания с Docker и полным monitoring stack, но критически нуждается в CI/CD автоматизации, backup стратегии и production security настройках. После добавления этих компонентов система будет готова к enterprise-level деплою.
