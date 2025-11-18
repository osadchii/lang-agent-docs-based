# Интеграция с Telegram

## Обзор архитектуры

Наше приложение использует **два компонента Telegram**:

1. **Telegram Bot** - для диалога с ИИ-преподавателем через текстовые сообщения
2. **Telegram Mini App** - для практики (карточки, упражнения) и управления профилем/группами

**Разделение ответственности:**

| Функция | Telegram Bot | Telegram Mini App |
|---------|--------------|-------------------|
| Диалог с ИИ | ✅ | ❌ |
| Добавление слов из диалога | ✅ | ✅ (ручное добавление) |
| Практика карточек | ✅ (упрощенная) | ✅ (полная) |
| Упражнения | ✅ (текстовые) | ✅ (текстовые + выбор) |
| Управление профилями | ✅ (переключение) | ✅ (полное) |
| Управление колодами | ✅ (выбор активной) | ✅ (CRUD) |
| Управление темами | ✅ (выбор активной) | ✅ (CRUD) |
| Группы | ❌ | ✅ |
| Статистика | ✅ (краткая) | ✅ (подробная) |
| Уведомления (стрик) | ✅ | ✅ (через Mini App) |

**Особенности реализации в боте:**
- **Карточки:** Показ по одной, кнопки "Взять карточку", "Перевернуть карточку", оценка (Не знаю/Повторить/Знаю)
- **Упражнения:** Одно упражнение за раз, только текстовый ввод, проверка через LLM
- **Профили:** Переключение через `/switch_profile` и inline-кнопки
- **Колоды:** Выбор активной через `/decks` (карточки берутся из активной колоды)
- **Темы:** Выбор активной через `/topics` (упражнения генерируются по активной теме)

**Особенности реализации в Mini App:**
- **Карточки:** Режим сессии (10-20 карточек), анимация переворота, статистика сессии, режим браузера
- **Упражнения:** Сессии 5-10 заданий, множественный выбор + текстовый ввод, детальная обратная связь
- **Профили:** Создание, редактирование, удаление
- **Колоды/Темы:** Полное CRUD управление, переименование, удаление
- **Группы:** Создание, управление участниками, шаринг материалов

---

## 1. Telegram Bot API

### 1.1. Библиотека

**Рекомендуется:** `python-telegram-bot` (современная версия 20+)

```bash
pip install python-telegram-bot[webhooks]
```

**Альтернативы:**
- `aiogram` - асинхронная библиотека (если нужна высокая производительность)
- `pyTelegramBotAPI` (telebot) - простая синхронная библиотека

**Для нашего проекта:** `python-telegram-bot` с асинхронным подходом

### 1.2. Основная структура бота

```python
# bot.py
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes
)
import logging

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


class LanguageLearningBot:
    def __init__(self, token: str):
        self.application = Application.builder().token(token).build()
        self._register_handlers()

    def _register_handlers(self):
        """Регистрирует все handlers бота."""
        # Команды
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("profile", self.profile_command))
        self.application.add_handler(CommandHandler("app", self.open_mini_app_command))
        self.application.add_handler(CommandHandler("stats", self.stats_command))

        # Команды для карточек
        self.application.add_handler(CommandHandler("card", self.get_card_command))
        self.application.add_handler(CommandHandler("decks", self.list_decks_command))

        # Команды для упражнений
        self.application.add_handler(CommandHandler("exercise", self.get_exercise_command))
        self.application.add_handler(CommandHandler("topics", self.list_topics_command))

        # Текстовые сообщения (диалог с LLM)
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text_message)
        )

        # Callback queries (inline кнопки)
        self.application.add_handler(CallbackQueryHandler(self.handle_callback))

        # Обработка ошибок
        self.application.add_error_handler(self.error_handler)

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка команды /start."""
        user = update.effective_user
        telegram_id = user.id

        # Создаем или получаем пользователя из БД
        db_user = await get_or_create_user(
            telegram_id=telegram_id,
            first_name=user.first_name,
            last_name=user.last_name,
            username=user.username
        )

        # Проверяем, есть ли у пользователя профили
        profiles = await get_user_profiles(db_user.id)

        if not profiles:
            # Новый пользователь - предлагаем онбординг через Mini App
            keyboard = [
                [InlineKeyboardButton("Начать обучение 🚀", web_app={"url": f"{MINI_APP_URL}?start=onboarding"})]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.message.reply_text(
                f"Привет, {user.first_name}! 👋\n\n"
                "Я твой личный ИИ-преподаватель. Помогу тебе выучить любой язык через:\n"
                "• 💬 Разговорную практику\n"
                "• 🎴 Карточки для запоминания слов\n"
                "• 📝 Упражнения на грамматику\n"
                "• 👥 Обучение в группах\n\n"
                "Давай начнем с быстрой настройки!",
                reply_markup=reply_markup
            )
        else:
            # Существующий пользователь
            active_profile = next((p for p in profiles if p.is_active), profiles[0])

            keyboard = [
                [InlineKeyboardButton("Открыть приложение 📱", web_app={"url": MINI_APP_URL})],
                [
                    InlineKeyboardButton("Практика 🎴", callback_data="practice"),
                    InlineKeyboardButton("Статистика 📊", callback_data="stats")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.message.reply_text(
                f"С возвращением, {user.first_name}! 🎉\n\n"
                f"Активный профиль: {active_profile.language_name} ({active_profile.current_level})\n"
                f"Стрик: {active_profile.streak} дней 🔥\n\n"
                "Чем займемся сегодня?",
                reply_markup=reply_markup
            )

    async def handle_text_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка текстовых сообщений - диалог с LLM или ответ на упражнение."""
        user = update.effective_user
        message_text = update.message.text

        # Получаем пользователя и активный профиль
        db_user = await get_user_by_telegram_id(user.id)
        if not db_user:
            await update.message.reply_text("Пожалуйста, сначала выполните /start")
            return

        active_profile = await get_active_profile(db_user.id)
        if not active_profile:
            await update.message.reply_text(
                "У вас нет активного профиля. Создайте его в приложении:",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("Открыть приложение", web_app={"url": MINI_APP_URL})
                ]])
            )
            return

        # Проверяем, есть ли активное упражнение
        if 'current_exercise' in context.user_data:
            exercise_id = context.user_data['current_exercise']
            del context.user_data['current_exercise']  # Удаляем из контекста

            # Проверяем ответ через LLM
            await update.message.chat.send_action("typing")

            result = await check_exercise_answer(
                exercise_id=exercise_id,
                user_answer=message_text
            )

            # Формируем ответ
            result_emoji = {"correct": "✅", "partial": "🟡", "incorrect": "❌"}
            result_text_map = {"correct": "Правильно!", "partial": "Почти правильно", "incorrect": "Неправильно"}

            response_text = (
                f"{result_emoji[result.result]} *{result_text_map[result.result]}*\n\n"
                f"*Ваш ответ:* {message_text}\n"
                f"*Правильный ответ:* {result.correct_answer}\n\n"
                f"💡 {result.explanation}"
            )

            if result.alternatives:
                response_text += f"\n\n*Альтернативы:* {', '.join(result.alternatives)}"

            keyboard = [
                [InlineKeyboardButton("Следующее упражнение 📝", callback_data="get_exercise")],
                [InlineKeyboardButton("Открыть приложение 📱", web_app={"url": f"{MINI_APP_URL}?start=exercises"})]
            ]

            await update.message.reply_text(
                response_text,
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

            # Сохраняем результат в истории
            await save_exercise_result(
                user_id=db_user.id,
                exercise_id=exercise_id,
                user_answer=message_text,
                result=result.result
            )

            return

        # Проверяем лимит сообщений
        if not await check_message_limit(db_user):
            await update.message.reply_text(
                "Вы достигли дневного лимита сообщений (50 для бесплатного плана).\n\n"
                "Оформите Premium для 500 сообщений в день!",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("Оформить Premium 💎", callback_data="upgrade_premium")
                ]])
            )
            return

        # Отправляем typing action
        await update.message.chat.send_action("typing")

        # Отправляем сообщение в LLM
        try:
            llm_response = await process_user_message(
                user=db_user,
                profile=active_profile,
                message=message_text,
                conversation_history=await get_conversation_history(db_user.id, active_profile.id)
            )

            # Сохраняем историю
            await save_message_to_history(
                user_id=db_user.id,
                profile_id=active_profile.id,
                role="user",
                content=message_text
            )
            await save_message_to_history(
                user_id=db_user.id,
                profile_id=active_profile.id,
                role="assistant",
                content=llm_response.text
            )

            # Инкрементируем счетчик
            await increment_message_usage(db_user)

            # Отправляем ответ
            await update.message.reply_text(llm_response.text)

            # Если LLM предложил добавить слова - показываем кнопку
            if llm_response.suggested_words:
                keyboard = [[
                    InlineKeyboardButton(
                        f"Добавить слова в колоду ({len(llm_response.suggested_words)})",
                        callback_data=f"add_words:{','.join(llm_response.suggested_words)}"
                    )
                ]]
                await update.message.reply_text(
                    "Хотите добавить новые слова в карточки?",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            else:
                # Показываем кнопки для практики (если нет suggested_words)
                keyboard = [
                    [
                        InlineKeyboardButton("Взять карточку 🎴", callback_data="get_card"),
                        InlineKeyboardButton("Упражнение 📝", callback_data="get_exercise")
                    ]
                ]
                await update.message.reply_text(
                    "Хотите попрактиковаться?",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )

        except Exception as e:
            logger.error(f"Error processing message: {e}")
            await update.message.reply_text(
                "Произошла ошибка при обработке сообщения. Попробуйте еще раз."
            )

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка callback queries от inline кнопок."""
        query = update.callback_query
        await query.answer()

        callback_data = query.data

        if callback_data == "practice":
            # Показать варианты практики
            keyboard = [
                [InlineKeyboardButton("Карточки 🎴", callback_data="get_card")],
                [InlineKeyboardButton("Упражнение 📝", callback_data="get_exercise")],
                [InlineKeyboardButton("Открыть приложение 📱", web_app={"url": f"{MINI_APP_URL}?start=practice"})]
            ]
            await query.edit_message_text(
                "Выберите тип практики:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

        elif callback_data == "get_card":
            # Получить карточку из активной колоды
            user = await get_user_by_telegram_id(query.from_user.id)
            active_profile = await get_active_profile(user.id)
            active_deck = await get_active_deck(active_profile.id)

            # Получаем следующую карточку по алгоритму
            card = await get_next_card(active_deck.id)

            if not card:
                await query.edit_message_text(
                    "У вас пока нет карточек для изучения.\n\n"
                    "Добавьте слова через диалог со мной или через приложение!",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("Открыть приложение", web_app={"url": f"{MINI_APP_URL}?start=cards"})
                    ]])
                )
                return

            # Показываем карточку (случайная сторона)
            show_side = random.choice(['learning', 'native'])

            if show_side == 'learning':
                card_text = f"🎴 *Карточка*\n\n{card.word}\n\n_{card.example}_"
            else:
                card_text = f"🎴 *Карточка*\n\n{card.translation}\n\n_{card.example_translation}_"

            keyboard = [[
                InlineKeyboardButton("Перевернуть карточку 🔄", callback_data=f"flip_card:{card.id}:{show_side}")
            ]]

            await query.edit_message_text(
                card_text,
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

        elif callback_data.startswith("flip_card:"):
            # Перевернуть карточку
            _, card_id, current_side = callback_data.split(":")
            card = await get_card_by_id(card_id)

            # Показываем обе стороны
            card_text = (
                f"🎴 *Карточка*\n\n"
                f"*{card.word}* — {card.translation}\n\n"
                f"_{card.example}_\n"
                f"_{card.example_translation}_"
            )

            keyboard = [
                [
                    InlineKeyboardButton("Не знаю ❌", callback_data=f"rate_card:{card.id}:dont_know"),
                    InlineKeyboardButton("Повторить 🔄", callback_data=f"rate_card:{card.id}:repeat"),
                    InlineKeyboardButton("Знаю ✅", callback_data=f"rate_card:{card.id}:know")
                ]
            ]

            await query.edit_message_text(
                card_text,
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

        elif callback_data.startswith("rate_card:"):
            # Оценка карточки
            _, card_id, rating = callback_data.split(":")

            # Обновляем интервал повторения
            card = await rate_card(card_id, rating)

            # Показываем результат
            rating_emoji = {"dont_know": "❌", "repeat": "🔄", "know": "✅"}
            rating_text = {"dont_know": "Не знаю", "repeat": "Повторить", "know": "Знаю"}

            result_text = (
                f"{rating_emoji[rating]} *{rating_text[rating]}*\n\n"
                f"Следующий показ через {card.interval_days} дней\n"
                f"Дата: {card.next_review.strftime('%d.%m.%Y')}"
            )

            keyboard = [
                [InlineKeyboardButton("Следующая карточка 🎴", callback_data="get_card")],
                [InlineKeyboardButton("Открыть приложение 📱", web_app={"url": f"{MINI_APP_URL}?start=cards"})]
            ]

            await query.edit_message_text(
                result_text,
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

        elif callback_data == "get_exercise":
            # Получить упражнение по активной теме
            user = await get_user_by_telegram_id(query.from_user.id)
            active_profile = await get_active_profile(user.id)
            active_topic = await get_active_topic(active_profile.id)

            if not active_topic:
                await query.edit_message_text(
                    "У вас нет активной темы для упражнений.\n\n"
                    "Добавьте тему через /add_topic или выберите из списка /topics",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("Открыть приложение", web_app={"url": f"{MINI_APP_URL}?start=exercises"})
                    ]])
                )
                return

            # Проверяем лимит упражнений
            if not await check_exercise_limit(user):
                await query.edit_message_text(
                    "Вы достигли дневного лимита упражнений (10 для бесплатного плана).\n\n"
                    "Оформите Premium для неограниченных упражнений!",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("Оформить Premium 💎", callback_data="upgrade_premium")
                    ]])
                )
                return

            # Генерируем упражнение через LLM
            exercise = await generate_exercise(
                user=user,
                profile=active_profile,
                topic=active_topic
            )

            # Сохраняем в контексте для проверки ответа
            context.user_data['current_exercise'] = exercise.id

            exercise_text = (
                f"📝 *Упражнение: {active_topic.name}*\n\n"
                f"{exercise.question}\n\n"
                f"_{exercise.prompt}_\n\n"
                f"💡 Напишите ваш ответ в следующем сообщении"
            )

            keyboard = [[
                InlineKeyboardButton("Подсказка 💡", callback_data=f"hint_exercise:{exercise.id}")
            ]]

            await query.edit_message_text(
                exercise_text,
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

        elif callback_data == "stats":
            # Показать краткую статистику
            user = await get_user_by_telegram_id(query.from_user.id)
            active_profile = await get_active_profile(user.id)
            stats = await get_profile_stats(active_profile.id)

            await query.edit_message_text(
                f"📊 Ваша статистика ({active_profile.language_name}):\n\n"
                f"🔥 Стрик: {stats.streak} дней\n"
                f"🎴 Карточек изучено: {stats.cards_studied}\n"
                f"📝 Упражнений выполнено: {stats.exercises_completed}\n"
                f"⏱ Время обучения: {stats.total_minutes} минут\n\n"
                "Подробная статистика доступна в приложении.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("Открыть приложение", web_app={"url": MINI_APP_URL})
                ]])
            )

        elif callback_data.startswith("add_words:"):
            # Добавление слов в колоду
            words_str = callback_data.split(":", 1)[1]
            words = words_str.split(",")

            user = await get_user_by_telegram_id(query.from_user.id)
            active_profile = await get_active_profile(user.id)
            active_deck = await get_active_deck(active_profile.id)

            try:
                # Создаем карточки через LLM
                created_cards = await create_cards_from_words(
                    deck_id=active_deck.id,
                    words=words,
                    source_language=active_profile.language,
                    target_language="ru"
                )

                await query.edit_message_text(
                    f"✅ Добавлено {len(created_cards)} карточек в колоду '{active_deck.name}'!\n\n"
                    "Они будут доступны для изучения в приложении.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("Изучить сейчас 🎴", web_app={"url": f"{MINI_APP_URL}?start=cards"})
                    ]])
                )

            except Exception as e:
                logger.error(f"Error adding words: {e}")
                await query.edit_message_text("Произошла ошибка при добавлении слов.")

        elif callback_data == "upgrade_premium":
            # Предложить оформить Premium
            keyboard = [[
                InlineKeyboardButton("Оформить Premium 💎", web_app={"url": f"{MINI_APP_URL}?start=premium"})
            ]]
            await query.edit_message_text(
                "💎 Premium подписка:\n\n"
                "✅ 500 сообщений LLM в день (вместо 50)\n"
                "✅ Неограниченные карточки и упражнения\n"
                "✅ До 10 языковых профилей\n"
                "✅ Неограниченные группы\n"
                "✅ Приоритетная поддержка\n\n"
                "От 4.99€/месяц",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка ошибок."""
        logger.error(f"Exception while handling update: {context.error}")

    def run_webhook(self, webhook_url: str, port: int = 8443):
        """Запуск бота в режиме webhook."""
        self.application.run_webhook(
            listen="0.0.0.0",
            port=port,
            url_path=f"/telegram-webhook/{BOT_TOKEN}",
            webhook_url=f"{webhook_url}/telegram-webhook/{BOT_TOKEN}"
        )

    def run_polling(self):
        """Запуск бота в режиме long polling."""
        self.application.run_polling()


# Запуск
if __name__ == "__main__":
    bot = LanguageLearningBot(token=BOT_TOKEN)

    # Production: webhook
    if os.getenv("APP_ENV") == "production":
        bot.run_webhook(webhook_url=WEBHOOK_URL)
    # Development: polling
    else:
        bot.run_polling()
```

> ⚠️ Backend автоматически вызывает `setWebhook`, если указан `BACKEND_DOMAIN` (URL собирается как `https://<BACKEND_DOMAIN>`). Оставляйте домен закомментированным, пока DNS не прикручен к публичному адресу: приложение проверяет, что hostname резолвится, и иначе пропускает настройку (бот продолжит работу через polling).

---

### 1.3. Команды бота

**Список команд (BotFather):**

```
start - Начать работу с ботом
help - Помощь и список команд
app - Открыть приложение
profile - Мой профиль
stats - Статистика
settings - Настройки
```

**Детальное описание команд:**

#### /start

**Для новых пользователей:**
- Приветственное сообщение
- Краткое описание функций
- Кнопка "Начать обучение" (открывает Mini App с онбордингом)

**Для существующих:**
- Приветствие с именем
- Активный профиль и стрик
- Кнопки: "Открыть приложение", "Практика", "Статистика"

**Deep linking:**
```
/start onboarding - Открыть онбординг
/start practice - Открыть практику
/start premium - Открыть страницу Premium
```

#### /help

```python
async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
    🤖 Помощь по использованию бота

    *Основные функции:*
    • Просто пишите мне - я отвечу и помогу практиковать язык
    • Используйте /app для открытия приложения
    • /profile - ваш профиль и настройки
    • /stats - статистика обучения

    *Практика:*
    • 🎴 Карточки - для запоминания слов
    • 📝 Упражнения - грамматика и письмо
    • 💬 Диалог со мной - разговорная практика

    *Группы:*
    • Создавайте группы для совместного обучения
    • Делитесь материалами с учениками

    По всем вопросам: @support_username
    """
    await update.message.reply_text(help_text, parse_mode="Markdown")
```

#### /app

```python
async def open_mini_app_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[
        InlineKeyboardButton("Открыть приложение 📱", web_app={"url": MINI_APP_URL})
    ]]
    await update.message.reply_text(
        "Нажмите на кнопку, чтобы открыть приложение:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
```

#### /profile

```python
async def profile_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = await get_user_by_telegram_id(update.effective_user.id)
    profiles = await get_user_profiles(user.id)
    active_profile = next((p for p in profiles if p.is_active), None)

    if active_profile:
        profile_text = f"""
        👤 *Ваш профиль*

        Язык: {active_profile.language_name}
        Уровень: {active_profile.current_level} → {active_profile.target_level}
        Стрик: {active_profile.streak} дней 🔥

        Карточек: {active_profile.cards_count}
        Упражнений: {active_profile.exercises_count}

        Подписка: {'Premium 💎' if user.is_premium else 'Free'}
        """

        keyboard = [[
            InlineKeyboardButton("Редактировать профиль", web_app={"url": f"{MINI_APP_URL}?start=profile"})
        ]]

        await update.message.reply_text(
            profile_text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await update.message.reply_text("У вас нет профилей. Создайте первый профиль в приложении.")
```

#### /stats

Показывает краткую статистику (подробная в Mini App).

---

### 1.4. Обработка входящих сообщений

#### Текстовые сообщения

**Типы сообщений:**
1. **Команды** - обрабатываются CommandHandler
2. **Обычный текст** - диалог с LLM через MessageHandler

**Фильтры:**
```python
# Только текст, исключая команды
MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message)
```

#### Голосовые сообщения

**Реализовано в `app/telegram/bot.TelegramBot._handle_voice_message`.**

Флоу:

1. Проверяем лимиты `VOICE_MAX_DURATION_SECONDS` и `VOICE_MAX_FILE_SIZE_BYTES`. При превышении отвечаем пользователю и не ходим в OpenAI.
2. Скачиваем OGG через `context.bot.get_file(...)`, дополнительно сверяем фактический размер payload.
3. Передаём байты в `SpeechToTextService` (`app/services/speech_to_text.py`), который вызывает Whisper (`VOICE_TRANSCRIPTION_MODEL`, `VOICE_TRANSCRIPTION_TIMEOUT`) и возвращает `SpeechToTextResult`.
4. Если транскрипт пустой — отвечаем ошибкой. В остальных случаях текст передаётся в тот же `DialogService`, что и обычные сообщения, поэтому строка сразу сохраняется в `conversation_history`.

```python
async def handle_voice_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
    voice = update.message.voice
    if voice.duration > settings.voice_max_duration_seconds:
        await update.message.reply_text("⚠️ Голосовое сообщение слишком длинное.")
        return

    file = await context.bot.get_file(voice.file_id)
    audio_bytes = await file.download_as_bytearray()

    transcript = await speech_to_text.transcribe(
        audio_bytes,
        language_hint=profile.language,
    )

    await dialog_service.process_message(
        user=db_user,
        profile_id=profile.id,
        message=transcript.text,
    )
```

Регистрация остаётся прежней:

```python
self.application.add_handler(MessageHandler(filters.VOICE, self.handle_voice_message))
```

#### Фото и документы

**Не используется в основном флоу**, но можно обрабатывать:

```python
async def handle_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка фотографий (например, текст на фото для перевода)."""
    photo = update.message.photo[-1]  # Берем самое большое разрешение

    # Скачать и обработать через OCR
    file = await context.bot.get_file(photo.file_id)
    # ...
```

#### Callback Queries (Inline кнопки)

**Структура callback_data:**
- Простой action: `"practice"`, `"stats"`, `"upgrade_premium"`
- С параметрами: `"add_words:casa,perro,gato"`, `"select_profile:uuid"`

**Обработка:**
```python
async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()  # ВАЖНО: всегда вызывать answer()

    callback_data = query.data

    if callback_data.startswith("add_words:"):
        words = callback_data.split(":", 1)[1].split(",")
        # Обработка...
    # ...
```

**Ограничения:**
- `callback_data` максимум 64 байта
- Для больших данных использовать БД: `callback_data="action:uuid"`

---

### 1.5. Клавиатуры и меню

#### Inline Keyboard (InlineKeyboardMarkup)

**Преимущества:**
- Кнопки под сообщением
- Поддержка callback_data
- Поддержка web_app (для открытия Mini App)
- Поддержка URL

**Примеры:**

```python
# 1. Web App кнопка
keyboard = [[
    InlineKeyboardButton("Открыть приложение 📱", web_app={"url": MINI_APP_URL})
]]

# 2. Callback кнопки
keyboard = [
    [
        InlineKeyboardButton("Практика 🎴", callback_data="practice"),
        InlineKeyboardButton("Статистика 📊", callback_data="stats")
    ],
    [InlineKeyboardButton("Настройки ⚙️", callback_data="settings")]
]

# 3. URL кнопка
keyboard = [[
    InlineKeyboardButton("Открыть сайт 🌐", url="https://example.com")
]]

# 4. Комбинация
keyboard = [
    [InlineKeyboardButton("Открыть приложение", web_app={"url": MINI_APP_URL})],
    [
        InlineKeyboardButton("Практика", callback_data="practice"),
        InlineKeyboardButton("Статистика", callback_data="stats")
    ]
]

reply_markup = InlineKeyboardMarkup(keyboard)
await update.message.reply_text("Текст", reply_markup=reply_markup)
```

#### Reply Keyboard (ReplyKeyboardMarkup)

**НЕ используется в нашем проекте**, потому что:
- Mini App - основной интерфейс
- Reply keyboard занимает много места
- Inline keyboard более гибкая

**Если нужно:**
```python
from telegram import ReplyKeyboardMarkup, KeyboardButton

keyboard = [
    [KeyboardButton("Практика 🎴"), KeyboardButton("Статистика 📊")],
    [KeyboardButton("Настройки ⚙️")]
]

reply_markup = ReplyKeyboardMarkup(
    keyboard,
    resize_keyboard=True,  # Автоматический размер
    one_time_keyboard=False  # Не скрывать после нажатия
)
```

#### Menu Button (Telegram Bot Menu)

**Настраивается через BotFather:**
```
/setmenubutton → выбрать бота → вставить URL Mini App
```

**Альтернатива через API:**
```python
await context.bot.set_chat_menu_button(
    menu_button={
        "type": "web_app",
        "text": "Открыть приложение",
        "web_app": {"url": MINI_APP_URL}
    }
)
```

---

### 1.6. Webhook vs Long Polling

#### Long Polling (для Development)

**Принцип работы:**
1. Бот делает запрос к Telegram: "Есть новые обновления?"
2. Telegram держит соединение открытым до новых сообщений (до 30 сек)
3. При получении обновлений - возвращает их
4. Бот обрабатывает и делает новый запрос

**Преимущества:**
- Просто настроить (не нужен SSL, домен)
- Идеально для разработки и тестирования

**Недостатки:**
- Постоянное соединение (больше ресурсов)
- Задержка до 1-2 секунд
- Не подходит для high-load

**Настройка:**
```python
def run_polling(self):
    """Запуск бота в режиме long polling."""
    self.application.run_polling(
        allowed_updates=Update.ALL_TYPES,  # Какие обновления получать
        drop_pending_updates=True  # Пропустить старые обновления при старте
    )
```

#### Webhook (для Production)

**Принцип работы:**
1. Telegram отправляет POST запрос на ваш сервер при новом обновлении
2. Сервер обрабатывает и возвращает 200 OK
3. Никаких постоянных соединений

**Преимущества:**
- Мгновенная доставка обновлений
- Меньше ресурсов сервера
- Масштабируемость
- Telegram рекомендует для production

**Недостатки:**
- Нужен SSL сертификат (HTTPS)
- Нужен публичный домен
- Сложнее настроить

**Настройка:**

1. **Установить webhook:**
```python
async def set_webhook(bot_token: str, webhook_url: str):
    """Устанавливает webhook для бота."""
    url = f"https://api.telegram.org/bot{bot_token}/setWebhook"
    data = {
        "url": f"{webhook_url}/telegram-webhook/{bot_token}",
        "allowed_updates": ["message", "callback_query"],
        "drop_pending_updates": True
    }

    response = requests.post(url, json=data)
    return response.json()
```

2. **Endpoint для приема обновлений (FastAPI):**
```python
from fastapi import FastAPI, Request
from telegram import Update

app = FastAPI()

@app.post("/telegram-webhook/{bot_token}")
async def telegram_webhook(bot_token: str, request: Request):
    """
    Endpoint для приема обновлений от Telegram.
    """
    # Проверяем токен
    if bot_token != BOT_TOKEN:
        return {"error": "Invalid token"}

    # Получаем JSON
    data = await request.json()

    # Создаем Update объект
    update = Update.de_json(data, bot.application.bot)

    # Передаем в обработчик
    await bot.application.process_update(update)

    return {"ok": True}
```

3. **Nginx конфигурация:**
```nginx
server {
    listen 443 ssl http2;
    server_name yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

    location /telegram-webhook/ {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

**Рекомендация для нашего проекта:**
- **Development:** Long Polling
- **Production:** Webhook

---

### 1.7. Уведомления через бота

#### Напоминания о стрике

**Проблема:** Пользователи находятся в разных часовых поясах, и мы хотим отправлять уведомления в 18:00 по **их локальному времени**.

**Решение:** Запускать задачу каждый час и проверять, для кого сейчас 18:00 по их часовому поясу.

**Хранение таймзоны:**
- В таблице `users` добавляем поле `timezone` (например, "Europe/Moscow", "America/New_York")
- При первом запуске бота определяем таймзону из `language_code` (приблизительно) или из Telegram API
- Пользователь может изменить в настройках через Mini App

```python
import asyncio
from datetime import datetime, timedelta
import pytz

async def send_streak_reminders():
    """
    Отправляет напоминания пользователям, для которых сейчас 18:00 по локальному времени.
    Запускается каждый час.
    """
    current_utc_time = datetime.now(pytz.UTC)

    # Получаем пользователей со стриком, которые еще не занимались сегодня
    # и у которых НЕТ отметки об отправке уведомления за сегодня
    users_to_check = await get_users_with_active_streak()

    for user in users_to_check:
        try:
            # Определяем локальное время пользователя
            user_timezone = pytz.timezone(user.timezone or 'UTC')
            user_local_time = current_utc_time.astimezone(user_timezone)

            # Проверяем, что сейчас 18:00 (с окном ±30 минут для надежности)
            if 17 <= user_local_time.hour < 19:
                # Проверяем, что еще не отправляли сегодня
                if await should_send_reminder(user.id, user_local_time.date()):
                    # Проверяем, что пользователь не занимался сегодня
                    if not await has_activity_today(user.id, user_local_time.date()):
                        await bot.application.bot.send_message(
                            chat_id=user.telegram_id,
                            text=f"🔥 Не забудьте о стрике!\n\n"
                                 f"У вас {user.current_streak} дней подряд обучения. "
                                 f"Сделайте хотя бы одно действие сегодня, чтобы сохранить стрик!",
                            reply_markup=InlineKeyboardMarkup([[
                                InlineKeyboardButton("Открыть приложение", web_app={"url": MINI_APP_URL})
                            ]])
                        )

                        # Помечаем, что уведомление отправлено
                        await mark_reminder_sent(user.id, user_local_time.date())

                        logger.info(f"Streak reminder sent to user {user.id} (timezone: {user.timezone}, local time: {user_local_time})")

        except Exception as e:
            logger.error(f"Failed to send reminder to {user.telegram_id}: {e}")

        # Небольшая задержка, чтобы не превысить rate limit Telegram
        await asyncio.sleep(0.05)  # 20 сообщений в секунду


async def should_send_reminder(user_id: str, today: date) -> bool:
    """
    Проверяет, было ли уже отправлено уведомление пользователю сегодня.
    """
    reminder = await db.query(StreakReminder).filter(
        StreakReminder.user_id == user_id,
        StreakReminder.sent_date == today
    ).first()

    return reminder is None


async def mark_reminder_sent(user_id: str, sent_date: date):
    """
    Помечает, что уведомление отправлено.
    """
    reminder = StreakReminder(
        user_id=user_id,
        sent_date=sent_date,
        sent_at=datetime.utcnow()
    )
    db.add(reminder)
    await db.commit()


# Запуск по расписанию (APScheduler, Celery, или cron)
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()

# Запускаем каждый час (в начале часа)
scheduler.add_job(send_streak_reminders, 'cron', hour='*', minute=0)

scheduler.start()
```

**Альтернативный подход (более эффективный для большого количества пользователей):**

```python
async def send_streak_reminders_optimized():
    """
    Оптимизированная версия: выбираем только пользователей,
    для которых сейчас примерно 18:00 по их таймзоне.
    """
    current_utc_time = datetime.now(pytz.UTC)
    current_utc_hour = current_utc_time.hour

    # Получаем все уникальные таймзоны из БД
    timezones = await db.query(User.timezone).distinct().all()

    for (tz_name,) in timezones:
        if not tz_name:
            continue

        try:
            tz = pytz.timezone(tz_name)
            local_time = current_utc_time.astimezone(tz)

            # Проверяем, что в этой таймзоне сейчас 18:00 (с окном)
            if 17 <= local_time.hour < 19:
                # Получаем пользователей с этой таймзоной
                users = await get_users_for_timezone_reminder(tz_name, local_time.date())

                for user in users:
                    try:
                        await bot.application.bot.send_message(
                            chat_id=user.telegram_id,
                            text=f"🔥 Не забудьте о стрике!\n\n"
                                 f"У вас {user.current_streak} дней подряд обучения. "
                                 f"Сделайте хотя бы одно действие сегодня, чтобы сохранить стрик!",
                            reply_markup=InlineKeyboardMarkup([[
                                InlineKeyboardButton("Открыть приложение", web_app={"url": MINI_APP_URL})
                            ]])
                        )

                        await mark_reminder_sent(user.id, local_time.date())
                        await asyncio.sleep(0.05)

                    except Exception as e:
                        logger.error(f"Failed to send reminder to {user.telegram_id}: {e}")

        except Exception as e:
            logger.error(f"Error processing timezone {tz_name}: {e}")
```

**Модель для отслеживания отправленных уведомлений:**

```python
class StreakReminder(Base):
    __tablename__ = 'streak_reminders'

    id = Column(UUID, primary_key=True, default=uuid4)
    user_id = Column(UUID, ForeignKey('users.id'), nullable=False)
    sent_date = Column(Date, nullable=False)  # Дата по локальному времени пользователя
    sent_at = Column(DateTime, default=datetime.utcnow)  # UTC время отправки

    __table_args__ = (
        # Уникальный constraint: одно уведомление на пользователя в день
        UniqueConstraint('user_id', 'sent_date', name='unique_user_reminder_per_day'),
    )
```

**Важные моменты:**

1. **Часовой пояс по умолчанию:** Если таймзона не установлена, используем UTC или определяем по `language_code`:
   ```python
   TIMEZONE_BY_LANGUAGE = {
       'ru': 'Europe/Moscow',
       'en': 'Europe/London',
       'es': 'Europe/Madrid',
       'de': 'Europe/Berlin',
       # и т.д.
   }
   ```

2. **Окно напоминания:** Используем окно 17:00-19:00, чтобы учесть возможные задержки и не пропустить пользователей

3. **Отслеживание отправки:** Храним отметку об отправке, чтобы не слать дубликаты

4. **Очистка старых записей:** Периодически удаляем записи старше 7 дней из `streak_reminders`

#### Приглашения в группы

```python
async def send_group_invite(user_telegram_id: int, group_name: str, inviter_name: str, invite_id: str):
    """Отправляет уведомление о приглашении в группу."""
    keyboard = [
        [
            InlineKeyboardButton("Принять ✅", callback_data=f"accept_invite:{invite_id}"),
            InlineKeyboardButton("Отклонить ❌", callback_data=f"decline_invite:{invite_id}")
        ]
    ]

    await bot.application.bot.send_message(
        chat_id=user_telegram_id,
        text=f"👥 Приглашение в группу\n\n"
             f"{inviter_name} приглашает вас в группу '{group_name}'.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
```

---

## 2. Telegram Mini App

### 2.1. Что такое Telegram Mini App

**Telegram Mini App** - это веб-приложение (HTML/CSS/JS), которое запускается внутри Telegram в WebView.

**Возможности:**
- Полноценный UI (React, Vue, Angular)
- Доступ к Telegram WebApp API
- Получение данных пользователя (через initData)
- Взаимодействие с ботом
- Платежи через Telegram Payments

**Ограничения:**
- Запускается только в Telegram
- Размер initial bundle должен быть небольшим (< 5 MB)
- Нет доступа к file system, camera, microphone (через WebView API)

---

### 2.2. Инициализация Mini App

#### React приложение

**Структура проекта:**
```
frontend/
├── public/
│   └── index.html
├── src/
│   ├── App.tsx
│   ├── hooks/
│   │   └── useTelegram.ts
│   ├── api/
│   │   └── client.ts
│   └── ...
└── package.json
```

**1. Подключение Telegram WebApp SDK:**

`public/index.html`:
```html
<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
  <title>Language Learning App</title>

  <!-- Telegram WebApp SDK -->
  <script src="https://telegram.org/js/telegram-web-app.js"></script>
</head>
<body>
  <div id="root"></div>
</body>
</html>
```

**2. TypeScript типы для Telegram WebApp:**

`src/types/telegram.d.ts`:
```typescript
interface TelegramWebApp {
  initData: string;
  initDataUnsafe: {
    user?: {
      id: number;
      first_name: string;
      last_name?: string;
      username?: string;
      language_code?: string;
    };
    start_param?: string;
  };
  version: string;
  platform: string;
  colorScheme: 'light' | 'dark';
  themeParams: {
    bg_color: string;
    text_color: string;
    hint_color: string;
    link_color: string;
    button_color: string;
    button_text_color: string;
  };
  isExpanded: boolean;
  viewportHeight: number;
  viewportStableHeight: number;
  headerColor: string;
  backgroundColor: string;
  BackButton: {
    isVisible: boolean;
    onClick: (callback: () => void) => void;
    offClick: (callback: () => void) => void;
    show: () => void;
    hide: () => void;
  };
  MainButton: {
    text: string;
    color: string;
    textColor: string;
    isVisible: boolean;
    isActive: boolean;
    isProgressVisible: boolean;
    setText: (text: string) => void;
    onClick: (callback: () => void) => void;
    offClick: (callback: () => void) => void;
    show: () => void;
    hide: () => void;
    enable: () => void;
    disable: () => void;
    showProgress: (leaveActive: boolean) => void;
    hideProgress: () => void;
  };
  HapticFeedback: {
    impactOccurred: (style: 'light' | 'medium' | 'heavy' | 'rigid' | 'soft') => void;
    notificationOccurred: (type: 'error' | 'success' | 'warning') => void;
    selectionChanged: () => void;
  };
  ready: () => void;
  expand: () => void;
  close: () => void;
  sendData: (data: string) => void;
  openLink: (url: string) => void;
  openTelegramLink: (url: string) => void;
  showPopup: (params: {
    title?: string;
    message: string;
    buttons: Array<{ id?: string; type: string; text?: string }>;
  }, callback?: (buttonId: string) => void) => void;
  showAlert: (message: string, callback?: () => void) => void;
  showConfirm: (message: string, callback?: (confirmed: boolean) => void) => void;
}

interface Window {
  Telegram: {
    WebApp: TelegramWebApp;
  };
}
```

**3. React Hook для Telegram WebApp:**

`src/hooks/useTelegram.ts`:
```typescript
import { useEffect, useState } from 'react';

export const useTelegram = () => {
  const [webApp, setWebApp] = useState<TelegramWebApp | null>(null);

  useEffect(() => {
    const tg = window.Telegram?.WebApp;
    if (tg) {
      tg.ready();
      tg.expand();
      setWebApp(tg);
    }
  }, []);

  return {
    webApp,
    user: webApp?.initDataUnsafe?.user,
    initData: webApp?.initData,
    colorScheme: webApp?.colorScheme,
    themeParams: webApp?.themeParams,
  };
};
```

**4. Аутентификация при запуске:**

`src/App.tsx`:
```typescript
import React, { useEffect, useState } from 'react';
import { useTelegram } from './hooks/useTelegram';
import { authenticateUser } from './api/auth';

function App() {
  const { initData, user } = useTelegram();
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [jwtToken, setJwtToken] = useState<string | null>(null);

  useEffect(() => {
    const authenticate = async () => {
      if (!initData) {
        console.error('No initData from Telegram');
        return;
      }

      try {
        // Отправляем initData на backend для валидации
        const response = await fetch('/api/auth/validate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ init_data: initData })
        });

        if (response.ok) {
          const data = await response.json();
          setJwtToken(data.token);
          localStorage.setItem('jwt_token', data.token);
          setIsAuthenticated(true);
        } else {
          console.error('Authentication failed');
        }
      } catch (error) {
        console.error('Authentication error:', error);
      }
    };

    authenticate();
  }, [initData]);

  if (!isAuthenticated) {
    return <div>Загрузка...</div>;
  }

  return (
    <div className="app">
      <h1>Привет, {user?.first_name}!</h1>
      {/* Основное приложение */}
    </div>
  );
}

export default App;
```

---

### 2.3. Взаимодействие с Telegram UI

#### Back Button

```typescript
import { useEffect } from 'react';
import { useTelegram } from './hooks/useTelegram';
import { useNavigate } from 'react-router-dom';

function SomeScreen() {
  const { webApp } = useTelegram();
  const navigate = useNavigate();

  useEffect(() => {
    if (!webApp) return;

    // Показываем кнопку "Назад"
    webApp.BackButton.show();

    // Обработчик нажатия
    const handleBackClick = () => {
      navigate(-1); // или navigate('/home')
    };

    webApp.BackButton.onClick(handleBackClick);

    // Cleanup
    return () => {
      webApp.BackButton.hide();
      webApp.BackButton.offClick(handleBackClick);
    };
  }, [webApp, navigate]);

  return <div>...</div>;
}
```

#### Main Button

```typescript
function CardReviewScreen() {
  const { webApp } = useTelegram();

  useEffect(() => {
    if (!webApp) return;

    // Настраиваем главную кнопку
    webApp.MainButton.setText('Завершить сессию');
    webApp.MainButton.show();
    webApp.MainButton.enable();

    const handleFinish = () => {
      // Обработка завершения
      finishSession();
    };

    webApp.MainButton.onClick(handleFinish);

    return () => {
      webApp.MainButton.hide();
      webApp.MainButton.offClick(handleFinish);
    };
  }, [webApp]);

  return <div>...</div>;
}
```

#### Haptic Feedback

```typescript
function CardRatingButtons() {
  const { webApp } = useTelegram();

  const handleRate = (rating: 'know' | 'repeat' | 'dont_know') => {
    // Тактильная обратная связь
    if (webApp) {
      if (rating === 'know') {
        webApp.HapticFeedback.notificationOccurred('success');
      } else if (rating === 'dont_know') {
        webApp.HapticFeedback.notificationOccurred('error');
      } else {
        webApp.HapticFeedback.impactOccurred('medium');
      }
    }

    // Оценка карточки
    rateCard(rating);
  };

  return (
    <div>
      <button onClick={() => handleRate('dont_know')}>Не знаю</button>
      <button onClick={() => handleRate('repeat')}>Повторить</button>
      <button onClick={() => handleRate('know')}>Знаю</button>
    </div>
  );
}
```

#### Popup, Alert, Confirm

```typescript
// Alert
webApp.showAlert('Карточка добавлена!', () => {
  console.log('Alert closed');
});

// Confirm
webApp.showConfirm('Удалить этот профиль?', (confirmed) => {
  if (confirmed) {
    deleteProfile();
  }
});

// Popup с кнопками
webApp.showPopup({
  title: 'Выберите действие',
  message: 'Что сделать с этой карточкой?',
  buttons: [
    { id: 'edit', type: 'default', text: 'Редактировать' },
    { id: 'delete', type: 'destructive', text: 'Удалить' },
    { id: 'cancel', type: 'cancel' }
  ]
}, (buttonId) => {
  if (buttonId === 'edit') {
    editCard();
  } else if (buttonId === 'delete') {
    deleteCard();
  }
});
```

---

### 2.4. Deep Linking

**Deep linking** позволяет открывать Mini App с определенным экраном/состоянием.

#### Из бота в Mini App

**1. Через web_app URL с параметрами:**

```python
# В боте
keyboard = [[
    InlineKeyboardButton(
        "Начать практику",
        web_app={"url": f"{MINI_APP_URL}?start=practice"}
    )
]]
```

**2. В React приложении:**

```typescript
function App() {
  const { webApp } = useTelegram();
  const navigate = useNavigate();

  useEffect(() => {
    const startParam = webApp?.initDataUnsafe?.start_param;

    if (startParam) {
      // Обработка deep link
      switch (startParam) {
        case 'onboarding':
          navigate('/onboarding');
          break;
        case 'practice':
          navigate('/practice/cards');
          break;
        case 'premium':
          navigate('/profile/premium');
          break;
        default:
          navigate('/home');
      }
    }
  }, [webApp, navigate]);

  return <RouterProvider router={router} />;
}
```

#### Из Mini App в бот

**Отправка данных боту:**

```typescript
// Отправить данные боту (бот получит через sendData callback)
webApp.sendData(JSON.stringify({
  action: 'card_completed',
  cardId: 'uuid',
  rating: 'know'
}));

// Бот должен быть в режиме inline для получения данных
```

**Открыть бот с параметром:**

```typescript
// Открыть чат с ботом
webApp.openTelegramLink('https://t.me/your_bot?start=from_miniapp');
```

---

### 2.5. Безопасность Telegram

#### Валидация initData

**КРИТИЧНО!** Детальный алгоритм описан в `backend-auth.md`.

**Краткая версия:**
1. Frontend получает `window.Telegram.WebApp.initData`
2. Отправляет на `/api/auth/validate`
3. Backend проверяет HMAC-SHA256 подпись
4. Backend возвращает JWT token
5. Все последующие запросы используют JWT

**Никогда не доверяйте:**
- `initDataUnsafe.user.id` без проверки (можно подделать в DevTools)
- Query parameters в URL
- localStorage/cookies (можно изменить)

**Всегда валидируйте:**
- initData через HMAC-SHA256 на backend
- JWT token в каждом запросе

---

## 3. Интеграция Bot ↔ Mini App

### 3.1. Сценарии взаимодействия

#### Сценарий 1: Добавление слов из диалога

**Флоу:**
1. Пользователь общается с ботом на изучаемом языке
2. LLM находит новые слова и предлагает добавить в карточки
3. Пользователь нажимает кнопку "Добавить слова"
4. Бот создает карточки через API
5. Пользователю предлагается открыть Mini App для изучения

**Код в боте:**
```python
# После ответа LLM
if llm_response.suggested_words:
    keyboard = [[
        InlineKeyboardButton(
            f"Добавить {len(llm_response.suggested_words)} слов в карточки",
            callback_data=f"add_words:{','.join(llm_response.suggested_words)}"
        )
    ]]
    await update.message.reply_text(
        "Нашел новые слова для вас:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# Callback handler
elif callback_data.startswith("add_words:"):
    words = callback_data.split(":", 1)[1].split(",")
    created_cards = await create_cards_from_words(deck_id, words)

    keyboard = [[
        InlineKeyboardButton("Изучить сейчас", web_app={"url": f"{MINI_APP_URL}?start=cards"})
    ]]
    await query.edit_message_text(
        f"✅ Добавлено {len(created_cards)} карточек!",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
```

#### Сценарий 2: Напоминание о стрике

**Флоу:**
1. Scheduler проверяет, кто не занимался сегодня
2. Бот отправляет напоминание с кнопкой открыть Mini App
3. Пользователь открывает Mini App
4. После любой активности стрик продлевается

**Код:**
```python
async def send_streak_reminder(user):
    keyboard = [[
        InlineKeyboardButton("Сохранить стрик 🔥", web_app={"url": MINI_APP_URL})
    ]]
    await bot.send_message(
        chat_id=user.telegram_id,
        text=f"🔥 У вас стрик {user.streak} дней!\n"
             f"Не забудьте позаниматься сегодня.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
```

---

## 4. Deployment

### 4.1. Environment Variables

```bash
# .env
BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
MINI_APP_URL=https://your-miniapp.com
BACKEND_DOMAIN=backend.external.osadchii.me
APP_ENV=production
```

### 4.2. Docker

```dockerfile
# Dockerfile для бота
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY bot.py .
COPY handlers/ ./handlers/

CMD ["python", "bot.py"]
```

```yaml
# docker-compose.yml
version: '3.8'

services:
  bot:
    build: ./bot
    env_file: .env
    depends_on:
      - postgres
      - redis
    restart: unless-stopped

  api:
    build: ./backend
    ports:
      - "8000:8000"
    env_file: .env
    depends_on:
      - postgres
      - redis

  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: langbot
      POSTGRES_USER: user
      POSTGRES_PASSWORD: password
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:
```

---

## 5. Best Practices

### 5.1. Error Handling

```python
async def handle_text_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        # Обработка сообщения
        ...
    except UserNotFoundError:
        await update.message.reply_text("Выполните /start для начала работы.")
    except RateLimitError:
        await update.message.reply_text("Вы достигли лимита. Попробуйте позже.")
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        await update.message.reply_text(
            "Произошла ошибка. Попробуйте позже или напишите @support"
        )
```

### 5.2. Rate Limiting

Telegram имеет свои лимиты:
- 30 сообщений в секунду для группового чата
- 20 сообщений в секунду для приватных чатов
- 1 сообщение в секунду на одного пользователя

**Защита от превышения:**
```python
import asyncio

async def send_bulk_messages(user_ids: list[int], text: str):
    for user_id in user_ids:
        try:
            await bot.send_message(user_id, text)
            await asyncio.sleep(0.05)  # 20 msg/sec
        except Exception as e:
            logger.error(f"Failed to send to {user_id}: {e}")
```

### 5.3. Logging

```python
import logging

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# В коде
logger.info(f"User {user.id} started conversation")
logger.warning(f"Rate limit exceeded for user {user.id}")
logger.error(f"Failed to process message: {e}", exc_info=True)
```

---

## Чеклист интеграции

**Перед запуском:**

- [ ] Bot token получен от @BotFather
- [ ] Команды настроены через @BotFather
- [ ] Menu button настроен (URL Mini App)
- [ ] Webhook настроен (production) или polling (dev)
- [ ] Mini App URL добавлен в переменные окружения
- [ ] initData валидация реализована на backend
- [ ] Deep linking работает (тестирование переходов)
- [ ] Error handling настроен
- [ ] Logging настроен
- [ ] Rate limiting учтен
- [ ] Тестирование всех команд
- [ ] Тестирование callback кнопок
- [ ] Тестирование уведомлений

---

Этот документ описывает полную интеграцию с Telegram Bot API и Mini App для приложения изучения языков с ИИ-преподавателем.
