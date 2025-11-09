# Language Learning AI Assistant

Telegram bot для изучения языков с ИИ-преподавателем. Проект включает интервальное повторение (SRS), генерацию упражнений через LLM, групповое обучение и интеграцию с Telegram Mini App.

## Документация

Полная документация проекта находится в директории `docs/`:

- [Архитектура](docs/architecture.md) - общая структура системы
- [Use Cases](docs/use-cases.md) - пользовательские сценарии
- [Backend API](docs/backend-api.md) - спецификация REST API
- [Развертывание](docs/deployment.md) - инструкции по деплою
- [Принципы разработки](docs/development-guidelines.md) - code style и best practices

## Структура проекта

```
.
├── backend/                 # FastAPI backend
│   ├── app/
│   │   ├── api/            # REST API endpoints
│   │   ├── core/           # Configuration, logging
│   │   ├── models/         # SQLAlchemy models (to be added)
│   │   ├── repositories/   # Data access layer (to be added)
│   │   └── services/       # Business logic (to be added)
│   ├── tests/              # Tests
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/               # React Mini App (to be added)
├── .github/workflows/      # CI/CD pipelines (to be added)
├── docs/                   # Project documentation
└── docker-compose.dev.yml  # Development environment
```

## Быстрый старт (Development)

### Требования

- Python 3.11+
- Docker и Docker Compose
- PostgreSQL 15+ (через Docker)
- Redis 7+ (через Docker)

### Установка

1. Клонировать репозиторий:
```bash
git clone <repository-url>
cd lang-agent-docs-based
```

2. Создать виртуальное окружение и установить зависимости:
```bash
cd backend
python -m venv venv
source venv/bin/activate  # или venv\Scripts\activate на Windows
pip install -r requirements.txt
```

3. Создать `.env` файл из примера:
```bash
cp .env.example .env
# Отредактировать .env и заполнить необходимые переменные
```

4. Запустить PostgreSQL и Redis через Docker:
```bash
cd ..
docker-compose -f docker-compose.dev.yml up -d
```

5. Запустить backend:
```bash
cd backend
uvicorn app.main:app --reload
```

Приложение будет доступно по адресу: http://localhost:8000

API документация: http://localhost:8000/api/docs

### Health Check

Проверить статус сервиса:
```bash
curl http://localhost:8000/api/health
```

## Разработка

### Code Style

Проект следует стандартам из `docs/development-guidelines.md`:

- **Black** для форматирования (line length: 100)
- **isort** для сортировки импортов
- **Ruff** для линтинга
- **mypy** для проверки типов

Запуск линтеров:
```bash
cd backend

# Форматирование
black app/
isort app/

# Линтинг
ruff check app/

# Type checking
mypy app/
```

### Тестирование

```bash
cd backend

# Запуск всех тестов
pytest

# С coverage
pytest --cov=app --cov-report=html

# Только unit tests
pytest tests/unit/
```

## Docker

### Разработка

```bash
# Запустить PostgreSQL + Redis
docker-compose -f docker-compose.dev.yml up -d

# Остановить
docker-compose -f docker-compose.dev.yml down

# Посмотреть логи
docker-compose -f docker-compose.dev.yml logs -f
```

### Production

```bash
# Build образа
cd backend
docker build -t langagent-backend:latest .

# Запуск
docker run -p 8000:8000 --env-file .env langagent-backend:latest
```

## Миграции базы данных

После реализации Alembic:

```bash
cd backend

# Создать новую миграцию
alembic revision --autogenerate -m "Description"

# Применить миграции
alembic upgrade head

# Откатить последнюю миграцию
alembic downgrade -1
```

## Roadmap

См. `to-do.md` для детального плана реализации.

**Текущий статус:** ✅ Foundation (задача 0) - завершена

Следующие задачи:
1. База данных и миграции (Alembic)
2. Конфигурация, безопасность и аутентификация
3. Rate limiting и лимиты тарифов
4. Пользователи и профили
5. Колоды и карточки (SRS)
...

## Лицензия

[Укажите лицензию]

## Контакты

[Укажите контакты]
