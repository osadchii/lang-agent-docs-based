# CI/CD Pipeline

## Обзор

CI/CD pipeline автоматизирует процесс тестирования, сборки и развертывания приложения:

- **На push в любой бранч**: запуск тестов и линтинга
- **На push в main или merge PR в main**: сборка backend-образа и публикация в GHCR (`ghcr.io/osadchii/lang-agent-docs-based/backend`)
- **Secrets**: секреты для CI/CD хранятся в GitHub Secrets, секреты приложения - в `.env` файле на сервере

## Как работает деплой

1. **GitHub Actions** собирает backend-образ и пушит его в GHCR
2. **Push в main** публикует теги `latest`, `sha`, `branch`; PR ветки проверяют только сборку
3. **На сервере** владелец вручную запускает `docker compose pull backend && docker compose up -d backend db redis`
4. Файл `.env` с переменными окружения **уже существует на сервере** и создается владельцем вручную перед первым деплоем

## Подготовка сервера (первый раз)

Перед первым деплоем владелец должен подготовить сервер:

### 1. Установка Docker и Docker Compose

```bash
# SSH на сервер
ssh user@your-server

# Установка Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Добавление пользователя в группу docker
sudo usermod -aG docker $USER

# Установка Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Проверка установки
docker --version
docker-compose --version
```

### 2. Создание директории и .env файла

```bash
# Создать директорию для приложения
sudo mkdir -p /var/app
cd /var/app

# Создать .env файл
sudo nano .env
```

Вставить содержимое (см. `docs/deployment.md` для полного списка переменных):
```bash
BACKEND_IMAGE=ghcr.io/osadchii/lang-agent-docs-based/backend
BACKEND_IMAGE_TAG=latest
POSTGRES_DB=langagent
POSTGRES_USER=postgres
POSTGRES_PASSWORD=secure_password
DATABASE_URL=postgresql://postgres:secure_password@db:5432/langagent
TELEGRAM_BOT_TOKEN=your_token
OPENAI_API_KEY=your_key
SECRET_KEY=your_secret_key
# ... и другие переменные
```

Установить безопасные права:
```bash
sudo chmod 600 .env
sudo chown $USER:$USER .env
```

### 3. Настройка SSH ключа для GitHub Actions

```bash
# Сгенерировать SSH ключ (на локальной машине)
ssh-keygen -t ed25519 -C "github-actions" -f ~/.ssh/github_actions

# Скопировать публичный ключ на сервер
ssh-copy-id -i ~/.ssh/github_actions.pub user@your-server

# Скопировать приватный ключ в буфер обмена
cat ~/.ssh/github_actions
# Добавить содержимое в GitHub Secrets как SSH_PRIVATE_KEY
```

После этого можно запускать деплой через GitHub Actions!

## GitHub Actions

Все workflows находятся в директории `.github/workflows/`.

### Workflow для backend

Весь backend pipeline живёт в одном workflow `.github/workflows/backend-deploy.yml`. Он включает:

- `tests` — запускается на **каждом push и pull request** для любых веток. Поднимает Postgres/Redis через services, ставит зависимости и гоняет `pytest --cov`.
- `build-and-push` — зависит от `tests` и выполняется **только для push в `main`**. Если тесты упали, сборка/публикация образа не стартует.

#### Файл: `.github/workflows/backend-deploy.yml`

Запускается при **каждом push / pull request** (обязательные тесты). Build/push выполняется только для push в `main`:

```yaml
name: Backend Deploy

on:
  push:
    branches:
      - '**'
  pull_request:
    branches:
      - '**'

env:
  IMAGE_NAME: ghcr.io/osadchii/lang-agent-docs-based/backend

jobs:
  tests:
    name: Backend Tests
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test
          POSTGRES_DB: langagent_test
        ports:
          - 5432:5432
        options: >-
          --health-cmd "pg_isready -U test -d langagent_test"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

      redis:
        image: redis:7-alpine
        ports:
          - 6379:6379
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: 'pip'
          cache-dependency-path: backend/requirements.txt

      - name: Install dependencies
        run: |
          cd backend
          python -m pip install --upgrade pip
          pip install -r requirements.txt

      - name: Run tests
        env:
          DATABASE_URL: postgresql+asyncpg://test:test@localhost:5432/langagent_test
          REDIS_URL: redis://localhost:6379/0
          SECRET_KEY: test-secret-key-for-ci
          TELEGRAM_BOT_TOKEN: test-telegram-token
          OPENAI_API_KEY: test-openai-key
        run: |
          cd backend
          pytest tests/ -v --cov=app --cov-report=term --cov-fail-under=85

  build-and-push:
    needs: tests
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Extract Docker metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ${{ env.IMAGE_NAME }}
          tags: |
            type=raw,value=latest
            type=sha,format=short
            type=ref,event=branch

      - name: Log in to GitHub Container Registry
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ secrets.GHCR_USERNAME }}
          password: ${{ secrets.GHCR_TOKEN }}

      - name: Build backend image
        uses: docker/build-push-action@v5
        with:
          context: ./backend
          file: ./backend/Dockerfile
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
```

Push-эвенты авторизуются в GHCR и публикуют теги `latest`, `sha` и `branch`. Job `build-and-push` запускается **только после успешного прохождения `tests`**, поэтому образ никогда не собирается при красных тестах. На pull_request (`push=false`) проверяется только сборка. После публикации сервер вручную тянет образ и перезапускает `docker-compose` (см. `docs/deployment.md` → Backend deployment).

### Workflow для frontend

#### Файл: `.github/workflows/frontend-test.yml`

Запускается при **каждом push** в любой бранч:

```yaml
name: Frontend Tests

on:
  push:
    branches:
      - '**'
    paths:
      - 'frontend/**'
      - '.github/workflows/frontend-test.yml'

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
          cache-dependency-path: frontend/package-lock.json

      - name: Install dependencies
        run: |
          cd frontend
          npm ci

      - name: Run linting
        run: |
          cd frontend
          npm run lint

      - name: Check formatting
        run: |
          cd frontend
          npm run format:check

      - name: TypeScript check
        run: |
          cd frontend
          npm run type-check

      - name: Run tests
        run: |
          cd frontend
          npm run test:ci

      - name: Build check
        run: |
          cd frontend
          npm run build
```

#### Файл: `.github/workflows/frontend-deploy.yml`

Запускается при **push в main** или **merge PR в main**:

```yaml
name: Frontend Deploy

on:
  push:
    branches:
      - main
    paths:
      - 'frontend/**'
      - '.github/workflows/frontend-deploy.yml'

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
          cache-dependency-path: frontend/package-lock.json

      - name: Install dependencies
        run: |
          cd frontend
          npm ci

      - name: Build
        env:
          VITE_API_BASE_URL: ${{ secrets.VITE_API_BASE_URL }}
          VITE_ENVIRONMENT: production
        run: |
          cd frontend
          npm run build

      - name: Deploy to server
        uses: appleboy/ssh-action@v1.0.3
        with:
          host: ${{ secrets.SERVER_HOST }}
          username: ${{ secrets.SERVER_USER }}
          key: ${{ secrets.SSH_PRIVATE_KEY }}
          script: |
            # Backup old build
            if [ -d /var/app/frontend/dist ]; then
              mv /var/app/frontend/dist /var/app/frontend/dist.backup
            fi

      - name: Upload build to server
        uses: appleboy/scp-action@v0.1.7
        with:
          host: ${{ secrets.SERVER_HOST }}
          username: ${{ secrets.SERVER_USER }}
          key: ${{ secrets.SSH_PRIVATE_KEY }}
          source: "frontend/dist"
          target: "/var/app/frontend/"
          strip_components: 1

      - name: Reload Nginx
        uses: appleboy/ssh-action@v1.0.3
        with:
          host: ${{ secrets.SERVER_HOST }}
          username: ${{ secrets.SERVER_USER }}
          key: ${{ secrets.SSH_PRIVATE_KEY }}
          script: |
            # Test Nginx config
            sudo nginx -t

            # Reload Nginx
            sudo systemctl reload nginx

            # Remove backup
            rm -rf /var/app/frontend/dist.backup

      - name: Notify on success
        if: success()
        uses: appleboy/telegram-action@master
        with:
          to: ${{ secrets.TELEGRAM_DEPLOY_CHAT_ID }}
          token: ${{ secrets.CI_TELEGRAM_BOT_TOKEN }}
          message: |
            ✅ Frontend deployed successfully!

            Branch: ${{ github.ref_name }}
            Commit: ${{ github.sha }}
            Author: ${{ github.actor }}

      - name: Notify on failure
        if: failure()
        uses: appleboy/telegram-action@master
        with:
          to: ${{ secrets.TELEGRAM_DEPLOY_CHAT_ID }}
          token: ${{ secrets.CI_TELEGRAM_BOT_TOKEN }}
          message: |
            ❌ Frontend deployment failed!

            Branch: ${{ github.ref_name }}
            Commit: ${{ github.sha }}
            Author: ${{ github.actor }}

            Check: https://github.com/${{ github.repository }}/actions/runs/${{ github.run_id }}
```

## Автоматизация деплоя

### Backend deploy steps

1. **Backend tests**:
   - Job `tests` поднимает сервисы Postgres/Redis и гоняет `pytest --cov`
   - Без зелёных тестов дальнейшие шаги не выполняются

2. **Checkout + Build**:
   - Используется `docker/build-push-action`
   - Собирает `backend/Dockerfile` внутри workflow
   - В событии `pull_request` push отключён (build-only)

3. **Генерация тегов**:
   - `docker/metadata-action` добавляет `latest`, `sha`, `branch`
   - Эти теги попадут в GHCR

4. **Публикация образа в GHCR**:
   - Авторизация через `GHCR_USERNAME`/`GHCR_TOKEN`
   - Push выполняется только на push в `main`
   - При необходимости можно добавить кэш (`cache-from/to`)

5. **Ручной деплой на сервер**:
   - Подключиться к серверу и выполнить `docker compose pull backend`
   - Применить миграции: `docker compose run --rm backend alembic upgrade head`
   - Перезапустить сервис: `docker compose up -d backend db redis`
   - Проверить `/health` (curl или мониторинг)

### Frontend deploy steps

1. **Build приложения**:
   - `npm ci` для установки зависимостей
   - `npm run build` для сборки production бандла
   - Переменные окружения из GitHub Secrets

2. **Backup старой версии**:
   - Сохранение текущей версии перед деплоем
   - Позволяет быстро откатиться при проблемах

3. **Upload на сервер**:
   - SCP копирование `frontend/dist/` на сервер
   - Размещение в `/var/app/frontend/dist/` (с `strip_components: 1` убирается префикс `frontend/`)

4. **Reload Nginx**:
   - Проверка конфигурации: `nginx -t`
   - Reload без простоя: `systemctl reload nginx`
   - Удаление backup после успешного деплоя

### Database migrations

Миграции исполняются внутри контейнера через `docker-entrypoint.sh` (команда `alembic upgrade head` запускается перед `uvicorn`). При ручном деплое:

```bash
docker compose pull backend
docker compose up -d backend
```

Контейнер выполнит миграции автоматически при старте. Если требуется отдельный запуск (например, перед выкладкой), выполните `docker compose run --rm backend alembic upgrade head`.

**Важно**:
- Следите за логами `docker compose logs -f backend` — ошибки миграций проявятся до старта приложения
- Перед продом проверяйте миграции локально
- Избегайте breaking changes без плана отката (`alembic downgrade`)

## Testing в CI

### Unit tests

**Backend (pytest)**:
```bash
cd backend
pytest tests/unit/ -v --cov=app --cov-report=term
```

Покрытие кода:
- Минимум 80% coverage
- Отчеты загружаются в Codecov
- PR блокируется при снижении coverage

**Frontend (Vitest)**:
```bash
cd frontend
npm run test:ci
```

### Integration tests

**Backend**:
```bash
cd backend
pytest tests/integration/ -v
```

Тесты с реальной БД:
- PostgreSQL в Docker через GitHub Services
- Тестирование API endpoints
- Проверка интеграции с LLM (мокирование)
- Тестирование Telegram webhook handlers

**Frontend**:
```bash
cd frontend
npm run test:integration
```

Тесты с React Testing Library:
- Рендеринг компонентов
- User interactions
- API мокирование (MSW)

### E2E tests (опционально)

Можно добавить Playwright или Cypress для end-to-end тестирования:

```yaml
# .github/workflows/e2e-tests.yml
name: E2E Tests

on:
  schedule:
    - cron: '0 2 * * *'  # Ежедневно в 2:00
  workflow_dispatch:

jobs:
  e2e:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Install Playwright
        run: |
          cd frontend
          npm ci
          npx playwright install --with-deps

      - name: Run E2E tests
        run: |
          cd frontend
          npm run test:e2e
        env:
          BASE_URL: https://yourdomain.com
```

## Required GitHub Secrets

Настройте следующие секреты в Settings → Secrets and variables → Actions:

### Backend image publishing (обязательные):
- `GHCR_USERNAME` — владелец контейнерного реестра (для текущего репо `osadchii`)
- `GHCR_TOKEN` — GitHub Personal Access Token с правами `write:packages` (и `read:packages`)

### Server deploy (опционально, для будущей автоматизации):
- `SERVER_HOST`, `SERVER_USER`, `SSH_PRIVATE_KEY` — понадобятся, когда добавим автоматический SSH-деплой
- `TELEGRAM_DEPLOY_CHAT_ID`, `CI_TELEGRAM_BOT_TOKEN` — для уведомлений о выкладке (пока не подключены)

### Frontend (обязательные):
- `VITE_API_BASE_URL` - URL бэкенд API (например, `https://api.yourdomain.com`)

**Важно**: Секреты приложения (DATABASE_URL, TELEGRAM_BOT_TOKEN, OPENAI_API_KEY и т.д.) НЕ добавляются в GitHub Secrets. Они хранятся только в файле `.env` на сервере.

## Notifications

Пока используем стандартные уведомления GitHub Actions (email / UI). Telegram‑бот подключаем после добавления автоматического деплоя.

## Rollback mechanism

### Ручной rollback

Для ручного отката на предыдущую версию:

```bash
# SSH на сервер
ssh user@your-server
cd /var/app

# Откатить на конкретный SHA (например, abc1234)
docker pull ghcr.io/osadchii/lang-agent-docs-based/backend:abc1234
docker tag ghcr.io/osadchii/lang-agent-docs-based/backend:abc1234 ghcr.io/osadchii/lang-agent-docs-based/backend:latest

# Откатить миграции
docker-compose exec backend alembic downgrade -1

# Перезапустить контейнеры
docker-compose restart backend

# Проверить статус
curl http://localhost:8000/health
docker-compose logs -f backend
```

## Best Practices

1. **Branch protection**:
   - Требовать прохождение всех тестов перед merge
   - Минимум 1 review для PR в main
   - Запретить force push в main

2. **Secrets rotation**:
   - Регулярно обновляйте SSH ключи
   - Переиздавайте GHCR токены (`GHCR_TOKEN`)
   - Ротация API ключей

3. **Monitoring**:
   - Следите за временем выполнения workflows
   - Используйте caching для ускорения
   - Мониторинг успешности деплоев

4. **Testing**:
   - Все новые фичи должны иметь тесты
   - Поддерживайте coverage выше 80%
   - Запускайте E2E тесты перед релизами

5. **Deploy strategy**:
   - Проводите smoke‑тест сразу после прод‑деплоя
   - Используйте feature flags для крупных изменений
   - Готовьте план rollback и бэкапы БД
