# CI/CD Pipeline

## Обзор

CI/CD pipeline автоматизирует процесс тестирования, сборки и развертывания приложения:

- **На push в любой бранч**: запуск тестов и линтинга
- **На push в main или merge PR в main**: build Docker образов + автоматический deploy на сервер
- **Secrets**: секреты для CI/CD хранятся в GitHub Secrets, секреты приложения - в `.env` файле на сервере

## Как работает деплой

1. **GitHub Actions** собирает Docker образы и пушит их в Docker Hub
2. **GitHub Actions** копирует `docker-compose.yml` из репозитория на сервер
3. На сервере выполняется:
   - `docker-compose pull` - скачивание новых образов
   - `docker-compose stop` - остановка старых контейнеров
   - Применение миграций БД
   - `docker-compose up -d` - запуск новых контейнеров
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
DOCKER_USERNAME=your_dockerhub_username
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

#### Файл: `.github/workflows/backend-test.yml`

Запускается при **каждом push** в любой бранч:

```yaml
name: Backend Tests

on:
  push:
    branches:
      - '**'
    paths:
      - 'backend/**'
      - '.github/workflows/backend-test.yml'

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test
          POSTGRES_DB: langagent_test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432

      redis:
        image: redis:7-alpine
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 6379:6379

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python 3.11
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: 'pip'

      - name: Install dependencies
        run: |
          cd backend
          pip install -r requirements.txt
          pip install pytest pytest-cov pytest-asyncio

      - name: Run linting
        run: |
          cd backend
          pip install black isort ruff mypy
          black --check --line-length 100 app
          isort --check --profile black app
          ruff check app
          mypy app --ignore-missing-imports

      - name: Run tests
        env:
          DATABASE_URL: postgresql://test:test@localhost:5432/langagent_test
          REDIS_URL: redis://localhost:6379/0
          SECRET_KEY: test-secret-key-for-ci
          TELEGRAM_BOT_TOKEN: test-token
          OPENAI_API_KEY: test-openai-key
        run: |
          cd backend
          pytest tests/ -v --cov=app --cov-report=xml --cov-report=term

      - name: Upload coverage reports
        uses: codecov/codecov-action@v4
        with:
          file: ./backend/coverage.xml
          flags: backend
```

#### Файл: `.github/workflows/backend-deploy.yml`

Запускается при **push в main** или **merge PR в main**:

```yaml
name: Backend Deploy

on:
  push:
    branches:
      - main
    paths:
      - 'backend/**'
      - 'docker-compose.yml'
      - '.github/workflows/backend-deploy.yml'

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Log in to Docker Hub
        uses: docker/login-action@v3
        with:
          username: ${{ secrets.DOCKER_USERNAME }}
          password: ${{ secrets.DOCKER_PASSWORD }}

      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ${{ secrets.DOCKER_USERNAME }}/langagent-backend
          tags: |
            type=sha,prefix=,format=short
            type=raw,value=latest

      - name: Build and push Docker image
        uses: docker/build-push-action@v5
        with:
          context: ./backend
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=registry,ref=${{ secrets.DOCKER_USERNAME }}/langagent-backend:buildcache
          cache-to: type=registry,ref=${{ secrets.DOCKER_USERNAME }}/langagent-backend:buildcache,mode=max

      - name: Copy docker-compose.yml to server
        uses: appleboy/scp-action@v0.1.7
        with:
          host: ${{ secrets.SERVER_HOST }}
          username: ${{ secrets.SERVER_USER }}
          key: ${{ secrets.SSH_PRIVATE_KEY }}
          source: "docker-compose.yml"
          target: "/var/app/"
          overwrite: true

      - name: Deploy to server
        uses: appleboy/ssh-action@v1.0.3
        with:
          host: ${{ secrets.SERVER_HOST }}
          username: ${{ secrets.SERVER_USER }}
          key: ${{ secrets.SSH_PRIVATE_KEY }}
          script: |
            cd /var/app

            # Pull latest images
            docker-compose pull backend

            # Stop old containers
            docker-compose stop backend

            # Run database migrations
            docker-compose run --rm backend alembic upgrade head

            # Start new containers
            docker-compose up -d backend

            # Wait for health check
            sleep 10
            curl -f http://localhost:8000/health || exit 1

            # Cleanup old images
            docker image prune -f

      - name: Notify on success
        if: success()
        uses: appleboy/telegram-action@master
        with:
          to: ${{ secrets.TELEGRAM_DEPLOY_CHAT_ID }}
          token: ${{ secrets.CI_TELEGRAM_BOT_TOKEN }}
          message: |
            ✅ Backend deployed successfully!

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
            ❌ Backend deployment failed!

            Branch: ${{ github.ref_name }}
            Commit: ${{ github.sha }}
            Author: ${{ github.actor }}

            Check: https://github.com/${{ github.repository }}/actions/runs/${{ github.run_id }}
```

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

1. **Build Docker image**:
   - Используется `docker/build-push-action`
   - Образ тегируется с commit SHA и `latest`
   - Кешируется для ускорения последующих сборок

2. **Push в Docker Hub**:
   - Авторизация через `DOCKER_USERNAME` и `DOCKER_PASSWORD` из GitHub Secrets
   - Push образа в Docker Hub registry

3. **Копирование docker-compose.yml на сервер**:
   - SCP копирование `docker-compose.yml` из репозитория в `/var/app/`
   - Перезаписывает существующий файл (`overwrite: true`)
   - `.env` файл на сервере **не трогается** - он уже создан владельцем

4. **Deploy на сервер**:
   - SSH подключение через `SSH_PRIVATE_KEY`
   - `docker-compose pull backend` - скачивание нового образа
   - `docker-compose stop backend` - остановка старого контейнера
   - `docker-compose run --rm backend alembic upgrade head` - применение миграций БД
   - `docker-compose up -d backend` - запуск нового контейнера
   - Health check для проверки: `curl -f http://localhost:8000/health`

5. **Cleanup**:
   - `docker image prune -f` - удаление старых образов для освобождения места

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

Миграции применяются автоматически в backend deploy workflow:

```bash
docker-compose run --rm backend alembic upgrade head
```

**Важно**:
- Миграции применяются **до** запуска нового контейнера
- Если миграция падает, деплой останавливается
- Логи миграций сохраняются в output GitHub Actions

**Безопасность миграций**:
- Используйте reversible миграции (`alembic downgrade`)
- Тестируйте миграции на staging перед production
- Избегайте breaking changes в одном деплое
- Используйте `op.batch_alter_table()` для больших таблиц

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
          BASE_URL: https://staging.yourdomain.com
```

## Required GitHub Secrets

Настройте следующие секреты в Settings → Secrets and variables → Actions:

### Backend & Deploy (обязательные):
- `DOCKER_USERNAME` - имя пользователя Docker Hub
- `DOCKER_PASSWORD` - пароль Docker Hub (или access token)
- `SERVER_HOST` - IP адрес или домен сервера (например, `192.168.1.100` или `example.com`)
- `SERVER_USER` - SSH пользователь (например, `ubuntu`, `root`)
- `SSH_PRIVATE_KEY` - приватный SSH ключ для доступа к серверу

### Frontend (обязательные):
- `VITE_API_BASE_URL` - URL бэкенд API (например, `https://api.yourdomain.com`)

### Notifications (опционально):
- `TELEGRAM_DEPLOY_CHAT_ID` - ID чата для уведомлений о деплое
- `CI_TELEGRAM_BOT_TOKEN` - токен отдельного бота для CI/CD уведомлений (НЕ основной бот приложения)

**Важно**: Секреты приложения (DATABASE_URL, TELEGRAM_BOT_TOKEN, OPENAI_API_KEY и т.д.) НЕ добавляются в GitHub Secrets. Они хранятся только в файле `.env` на сервере.

**Примечание**: `CI_TELEGRAM_BOT_TOKEN` - это токен отдельного бота для уведомлений CI/CD, не путать с `TELEGRAM_BOT_TOKEN` (основной бот приложения из .env файла).

## Notifications

Уведомления о статусе деплоя отправляются через Telegram:

- ✅ **Успешный деплой**: сообщение с деталями (branch, commit, автор)
- ❌ **Ошибка деплоя**: сообщение с ссылкой на GitHub Actions logs

Альтернативные способы:
- **Email**: GitHub может отправлять email при провале workflow
- **Slack**: используйте `slack-github-action`
- **Discord**: используйте webhook интеграцию

## Rollback mechanism

### Автоматический rollback при ошибках

Health check уже встроен в deploy workflow. Если он падает, деплой останавливается.

Для автоматического rollback можно добавить в `.github/workflows/backend-deploy.yml`:

```yaml
- name: Rollback on failure
  if: failure()
  uses: appleboy/ssh-action@v1.0.3
  with:
    host: ${{ secrets.SERVER_HOST }}
    username: ${{ secrets.SERVER_USER }}
    key: ${{ secrets.SSH_PRIVATE_KEY }}
    script: |
      cd /var/app

      # Откатить на предыдущий образ (сохраненный SHA)
      docker pull ${{ secrets.DOCKER_USERNAME }}/langagent-backend:PREVIOUS_SHA
      docker tag ${{ secrets.DOCKER_USERNAME }}/langagent-backend:PREVIOUS_SHA \
                 ${{ secrets.DOCKER_USERNAME }}/langagent-backend:latest

      # Откатить миграции
      docker-compose exec backend alembic downgrade -1

      # Перезапустить
      docker-compose restart backend
```

### Ручной rollback

Для ручного отката на предыдущую версию:

```bash
# SSH на сервер
ssh user@your-server
cd /var/app

# Посмотреть доступные образы
docker images | grep langagent-backend

# Откатить на конкретный SHA (например, abc1234)
docker pull username/langagent-backend:abc1234
docker tag username/langagent-backend:abc1234 username/langagent-backend:latest

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
   - Меняйте Docker Hub пароли
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
   - Деплой в staging перед production
   - Используйте feature flags для крупных изменений
   - Канареечные деплои для критичных обновлений
