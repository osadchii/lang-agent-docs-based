# Развертывание (Deployment)

## Окружения

### Локальное окружение
Локальная разработка выполняется с использованием:
- Backend: `uvicorn` в режиме hot-reload
- Frontend: `npm run dev` с Vite dev server
- База данных: PostgreSQL в Docker контейнере
- Redis: Redis в Docker контейнере
- Telegram bot: webhook в режиме polling для локальной разработки

Запуск:
```bash
# Инфраструктура (PostgreSQL + Redis)
docker-compose -f docker-compose.local.yml up -d

# Backend
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```

**docker-compose.local.yml (пример):**
```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: langagent_local
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: local_password
    ports:
      - "5432:5432"
    volumes:
      - postgres_local_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_local_data:/data

volumes:
  postgres_local_data:
  redis_local_data:
```

Опционально: для локальной отладки можно добавить Grafana и Loki в `docker-compose.local.yml` для просмотра логов и простых дашборд (см. этап C в `to-do.md`).

### Production
Продакшн окружение:
- VPS или облачный сервер (AWS, DigitalOcean, Hetzner и т.д.)
- PostgreSQL база данных
- Docker контейнеры для backend
- Статический хостинг для frontend (Nginx, Vercel, Netlify)
- Telegram bot с webhook для получения обновлений

## Инфраструктура

### Сервер
Рекомендуемая конфигурация:
- **CPU**: 2+ ядра
- **RAM**: 4+ GB
- **Disk**: 50+ GB SSD
- **OS**: Ubuntu 22.04 LTS или выше

Установленное ПО:
- Docker и Docker Compose
- Nginx (reverse proxy)
- Certbot (SSL сертификаты)

### База данных
PostgreSQL 15+:
- Размещение: тот же сервер или managed service (AWS RDS, DigitalOcean Managed DB)
- Настройки:
  - `max_connections`: 100
  - `shared_buffers`: 1GB
  - `work_mem`: 16MB
- Регулярные бэкапы (см. секцию Backup)
- Репликация для высокой доступности (опционально)

### Redis
Redis 7+ для кэширования и управления состоянием:
- **Использование:**
  - Кэширование (hot data: активный профиль, user stats)
  - Session storage (состояния диалогов бота FSM)
  - Rate limiting (счетчики для лимитов API)
  - LLM cache (переводы, лемматизация)
- **Размещение:** Docker контейнер на том же сервере или managed service (AWS ElastiCache, DigitalOcean Managed Redis)
- **Настройки:**
  - `maxmemory`: 512MB - 1GB
  - `maxmemory-policy`: allkeys-lru (вытеснение старых ключей)
  - Persistence: AOF (append-only file) для сохранения данных
- **Monitoring:**
  - Использование памяти (`INFO memory`)
  - Hit rate кэша
  - Количество подключений

**Примечание:** Redis является критичным компонентом для продакшена. Без Redis сервис не будет работать корректно.

### Storage
Хранение файлов (изображения, аудио):
- **Локальное хранение**: `/var/app/media` на сервере (для небольших объемов)
- **S3-совместимое хранилище**: AWS S3, MinIO, DigitalOcean Spaces (рекомендуется)
  - Автоматическое резервное копирование
  - CDN интеграция
  - Версионирование файлов

### CDN
Раздача статики фронтенда:
- **Nginx**: локальная раздача с кешированием
- **CloudFlare**: бесплатный CDN с SSL
- **AWS CloudFront**: для глобального распределения
- **Vercel/Netlify**: автоматический CDN при хостинге фронтенда

## Backend deployment

### Docker
Dockerfile для бэкенда (`backend/Dockerfile`) повторяет продовый сценарий запуска:
```dockerfile
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

RUN apt-get update \
    && apt-get install --no-install-recommends -y curl build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .

RUN adduser --disabled-password --gecos "" appuser \
    && chown -R appuser:appuser /app \
    && chmod +x /app/docker-entrypoint.sh

USER appuser
ENV PYTHONPATH=/app

ENTRYPOINT ["/app/docker-entrypoint.sh"]
```

Точка входа (`backend/docker-entrypoint.sh`) перед стартом `uvicorn` выполняет миграции:
```bash
#!/usr/bin/env bash
set -euo pipefail

alembic upgrade head

exec uvicorn app.main:app --host "0.0.0.0" --port "${PORT:-8000}"
```

Docker Compose для деплоя (`docker-compose.yml` в корне репозитория):
```yaml
version: '3.9'

services:
  backend:
    image: "${BACKEND_IMAGE:-ghcr.io/osadchii/lang-agent-docs-based/backend}:${BACKEND_IMAGE_TAG:-latest}"
    ports:
      - "8000:8000"
    env_file:
      - .env
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD-SHELL", "curl -fsS http://localhost:8000/health || exit 1"]
      interval: 30s
      timeout: 5s
      retries: 5
      start_period: 30s
    restart: unless-stopped
    networks:
      - app-network

  db:
    image: postgres:15
    env_file:
      - .env
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test:
        [
          "CMD-SHELL",
          "pg_isready -U $$POSTGRES_USER -d $$POSTGRES_DB",
        ]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped
    networks:
      - app-network

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 5
    restart: unless-stopped
    networks:
      - app-network

volumes:
  postgres_data:
  redis_data:

networks:
  app-network:
    driver: bridge
```

**Важно**: Docker Compose использует уже собранный образ из GitHub Container Registry (`ghcr.io/osadchii/lang-agent-docs-based/backend`). Для smoke‑тестов по-прежнему можно выполнить `docker compose build backend`, но продакшн сценарий тянет готовые теги командой `docker compose pull backend`.

### Environment variables

Файл `.env` создается **вручную на сервере** владельцем проекта перед первым деплоем и хранится в `/var/app/.env`.

**Содержимое `.env` файла:**
```bash
# Контейнеры
BACKEND_IMAGE=ghcr.io/osadchii/lang-agent-docs-based/backend
BACKEND_IMAGE_TAG=latest

# Database (для PostgreSQL контейнера)
POSTGRES_DB=langagent
POSTGRES_USER=postgres
POSTGRES_PASSWORD=secure_password_here

# Database URL (для backend)
DATABASE_URL=postgresql://postgres:secure_password_here@db:5432/langagent

# Redis
REDIS_URL=redis://redis:6379/0

# Telegram
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_WEBHOOK_URL=https://yourdomain.com/api/webhook

# OpenAI/LLM
OPENAI_API_KEY=your_openai_api_key
LLM_MODEL=gpt-4.1-mini
LLM_TEMPERATURE=0.7

# Anthropic (опционально)
ANTHROPIC_API_KEY=your_anthropic_key

# JWT/Security
SECRET_KEY=your_secret_key_here  # Генерируется один раз: openssl rand -hex 32
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30  # TTL для JWT access token (30 минут для безопасности)

# Environment
ENVIRONMENT=production  # local | production

# Stripe (для подписок)
STRIPE_SECRET_KEY=your_stripe_secret_key
STRIPE_WEBHOOK_SECRET=your_stripe_webhook_secret
STRIPE_PRICE_ID_BASIC=price_xxx
STRIPE_PRICE_ID_PREMIUM=price_yyy

# S3/Storage (опционально)
S3_BUCKET=your_bucket_name
S3_ACCESS_KEY=your_access_key
S3_SECRET_KEY=your_secret_key
S3_ENDPOINT=https://s3.amazonaws.com
```

**Создание .env файла на сервере:**
```bash
# SSH на сервер
ssh user@your-server

# Создать директорию для приложения
sudo mkdir -p /var/app
cd /var/app

# Создать .env файл
sudo nano .env
# Вставить переменные окружения и сохранить

# Установить безопасные права доступа
sudo chmod 600 .env
sudo chown $USER:$USER .env
```

**Важно**: `.env` файл НЕ коммитится в репозиторий и НЕ копируется из GitHub Actions. Он создается один раз на сервере и обновляется вручную при необходимости.

### Migrations
Применение миграций при деплое:

1. **Локально**:
```bash
alembic upgrade head
```

2. **В Docker контейнере**:
```bash
docker-compose exec backend alembic upgrade head
```

3. **Автоматически при старте** (добавить в entrypoint.sh):
```bash
#!/bin/bash
# Применение миграций
alembic upgrade head

# Запуск приложения
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
```

4. **В CI/CD pipeline**:
- Миграции применяются автоматически после успешного build
- См. `.github/workflows/deploy.yml`

### Запуск бота
Telegram бот запускается вместе с FastAPI приложением через Docker Compose:

```bash
cd /var/app
docker-compose up -d
```

Проверка статуса:
```bash
# Посмотреть запущенные контейнеры
docker-compose ps

# Логи backend
docker-compose logs -f backend

# Логи базы данных
docker-compose logs -f db
```

Webhook настраивается автоматически при старте приложения (см. `backend/app/telegram/bot.py`).

## Frontend deployment

### Build
Процесс сборки React приложения:

```bash
cd frontend
npm install
npm run build
```

Результат сборки находится в `frontend/dist/`:
- Оптимизированный JavaScript (минификация, tree-shaking)
- CSS с autoprefixer
- Оптимизированные изображения
- Service Worker для PWA (опционально)

### Hosting
Варианты размещения статики:

**1. Nginx на том же сервере:**
```nginx
server {
    listen 80;
    server_name yourdomain.com;

    root /var/app/frontend/dist;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

**2. Vercel/Netlify:**
- Автоматический деплой из GitHub
- Встроенный CDN
- SSL сертификаты
- Preview deployments для PR

**3. AWS S3 + CloudFront:**
- Статический хостинг
- Глобальный CDN
- Низкая стоимость

### Environment configuration
Переменные окружения для фронтенда настраиваются через `.env` файлы:

- `.env.development` - для локальной разработки
- `.env.production` - для продакшена

При деплое через CI/CD переменные подставляются автоматически из GitHub Secrets.

## Secrets management
Управление секретами (API ключи, токены):

### GitHub Secrets
Секреты для CI/CD хранятся в GitHub Secrets:
- Settings → Secrets and variables → Actions → New repository secret

Необходимые секреты для GitHub Actions:
- `GHCR_USERNAME` - владелец контейнерного реестра (например, `osadchii`)
- `GHCR_TOKEN` - GitHub Personal Access Token с правами `write:packages`
- `SSH_PRIVATE_KEY` - приватный SSH ключ для доступа к серверу
- `SERVER_HOST` - IP адрес или домен сервера
- `SERVER_USER` - SSH пользователь (например, `ubuntu`)
- `TELEGRAM_DEPLOY_CHAT_ID` - ID чата для уведомлений о деплое (опционально)
- `CI_TELEGRAM_BOT_TOKEN` - токен отдельного бота для CI/CD уведомлений (опционально, НЕ основной бот)

**Важно**: Секреты приложения (API ключи, токены БД и т.д.) НЕ хранятся в GitHub Secrets. Они находятся только в `.env` файле на сервере.

### На сервере
Все секреты приложения хранятся в файле `/var/app/.env` с ограниченными правами доступа:

```bash
# Установка безопасных прав доступа
chmod 600 /var/app/.env
chown $USER:$USER /var/app/.env
```

**Безопасность:**
- Файл `.env` доступен только владельцу
- Никогда не коммитьте `.env` в репозиторий
- Добавьте `.env` в `.gitignore`
- Создайте `.env.example` с пустыми значениями для документации

### Ротация секретов
Рекомендации:
- Менять `SECRET_KEY` каждые 90 дней
- API ключи менять при компрометации
- Использовать разные ключи для local/production
- При ротации секретов:
  1. Обновить `.env` файл на сервере
  2. Перезапустить контейнеры: `docker-compose restart backend`

## Мониторинг

### Логирование
Логи хранятся и анализируются:

**Docker logs:**
```bash
docker-compose logs -f backend
docker-compose logs --tail=100 backend
```

**Structured logging** в приложении:
- JSON формат для парсинга
- Уровни: DEBUG, INFO, WARNING, ERROR, CRITICAL
- Ротация логов (logrotate)

**Централизованное логирование:**
- ELK Stack (Elasticsearch, Logstash, Kibana)
- Loki + Grafana
- CloudWatch Logs (AWS)

### Алерты
Уведомления об ошибках:

**Sentry:**
- Автоматический трекинг ошибок
- Stack traces
- Группировка похожих ошибок
- Интеграция с Telegram/Slack

**Telegram bot для алертов:**
- Критические ошибки
- Недоступность сервиса
- Высокая нагрузка

**Email уведомления:**
- Резервный канал для критических алертов

### Метрики
Мониторинг производительности:

**Prometheus + Grafana:**
- CPU, RAM, Disk usage
- Request rate, latency
- Database queries performance
- Active users

**Application metrics:**
- Response time по эндпоинтам
- Количество активных пользователей
- Использование LLM API (tokens, cost)
- Успешность упражнений

**Health checks:**
- `/health` endpoint для проверки доступности
- Database connectivity check
- External APIs availability

## Backup
Резервное копирование БД и данных:

### База данных
**Ежедневные бэкапы:**
```bash
#!/bin/bash
# backup.sh
BACKUP_DIR=/var/backups/postgres
DATE=$(date +%Y%m%d_%H%M%S)
pg_dump -h localhost -U postgres langagent | gzip > $BACKUP_DIR/backup_$DATE.sql.gz

# Удаление старых бэкапов (старше 30 дней)
find $BACKUP_DIR -name "backup_*.sql.gz" -mtime +30 -delete
```

**Cron job:**
```bash
0 2 * * * /usr/local/bin/backup.sh
```

**Автоматическое копирование в S3:**
```bash
aws s3 cp $BACKUP_DIR/backup_$DATE.sql.gz s3://my-backups/database/
```

### Файлы пользователей
- Синхронизация в S3 (если используется локальное хранение)
- Версионирование в S3
- Регулярная проверка целостности

### Восстановление
```bash
# Восстановление из бэкапа
gunzip < backup_20250109.sql.gz | psql -h localhost -U postgres langagent

# Восстановление из S3
aws s3 cp s3://my-backups/database/backup_20250109.sql.gz .
gunzip < backup_20250109.sql.gz | psql -h localhost -U postgres langagent
```

## Rollback
Откат на предыдущую версию при проблемах:

### Процедура ручного rollback

1. **SSH на сервер:**
```bash
ssh user@your-server
cd /var/app
```

2. **Откатить Docker образ на предыдущую версию:**
```bash
# Посмотреть доступные версии образа
docker images | grep langagent-backend

# Обновить docker-compose.yml с нужной версией (SHA или тегом)
nano docker-compose.yml
# Изменить: image: username/langagent-backend:latest
# На: image: username/langagent-backend:abc1234 (предыдущий SHA)

# Или сделать pull конкретной версии
docker pull username/langagent-backend:abc1234
docker tag username/langagent-backend:abc1234 username/langagent-backend:latest
```

3. **Откатить миграции (если требуется):**
```bash
docker-compose exec backend alembic downgrade -1
```

4. **Перезапустить контейнеры:**
```bash
docker-compose down
docker-compose up -d
```

5. **Проверить работоспособность:**
```bash
# Health check
curl http://localhost:8000/health

# Логи
docker-compose logs -f backend
```

### Автоматический rollback
В CI/CD pipeline настроен автоматический откат при провале health checks после деплоя (см. `docs/ci-cd.md`).

### Восстановление из бэкапа
Если проблемы сохраняются после rollback:
```bash
# Восстановить БД из бэкапа
gunzip < /var/backups/postgres/backup_YYYYMMDD.sql.gz | \
  docker-compose exec -T db psql -U postgres -d langagent
```
