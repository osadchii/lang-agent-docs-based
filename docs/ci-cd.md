# CI/CD Pipeline

## GitHub Actions

### Workflow для backend

#### На push в main
- Запуск тестов
- Линтинг (flake8, black, mypy)
- Build Docker image
- Push в registry
- Deploy на сервер

#### На pull request
- Запуск тестов
- Линтинг
- Code review checks

### Workflow для frontend

#### На push в main
- Запуск тестов
- Линтинг (ESLint, Prettier)
- TypeScript проверка
- Build
- Deploy статики

#### На pull request
- Запуск тестов
- Линтинг
- Build check

## Автоматизация деплоя

### Backend deploy steps
TODO: описать шаги автоматического деплоя

### Frontend deploy steps
TODO: описать шаги автоматического деплоя

### Database migrations
TODO: автоматическое применение миграций

## Testing в CI

### Unit tests
TODO: запуск юнит-тестов

### Integration tests
TODO: запуск интеграционных тестов

### E2E tests (опционально)
TODO: end-to-end тестирование

## Notifications
TODO: уведомления о статусе деплоя (Telegram, email)

## Rollback mechanism
TODO: автоматический откат при ошибках
