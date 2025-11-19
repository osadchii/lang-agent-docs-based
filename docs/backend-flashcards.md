# Система карточек (Flashcards)

## Структура карточки

### Поля карточки
- Слово/фраза на изучаемом языке
- Перевод
- Транскрипция
- Примеры использования
- Изображение (опционально)
- Грамматические метки (род, падеж, время и т.д.)
- Теги

## Алгоритм повторений

### Spaced Repetition System (SRS)

**Выбор:** Упрощенная модификация алгоритма SM-2 (SuperMemo 2)

**Причины выбора:**
- ✅ Проверенная эффективность (используется в Anki, Duolingo)
- ✅ Простота реализации и понимания
- ✅ Отсутствие сложности расчета ease factor (фактор сложности)
- ✅ Фиксированные интервалы для предсказуемости
- ✅ Хорошо работает для изучения языков

**Отличия от классического SM-2:**
- Не используется ease factor (коэффициент легкости)
- Фиксированные множители интервалов вместо адаптивных
- Упрощенная система оценки (3 варианта вместо 6)

**Альтернативы (не выбраны):**
- Полный SM-2 - избыточная сложность для пользовательского опыта
- Anki-подобный - требует больше данных для калибровки
- Leitner System - менее гибкий, устаревший подход

### Интервалы повторений

#### Система оценок

**Три варианта оценки:**
1. **"Знаю"** (`know`) - пользователь правильно вспомнил
2. **"Повторить"** (`repeat`) - нужно повторить сегодня
3. **"Не знаю"** (`dont_know`) - забыл, нужно начать заново

#### Формула расчета интервалов

**Для новой карточки (статус `new`):**
```
interval = 0 (показывается сразу)
next_review = NOW()
```

**После первой оценки:**
```python
if rating == 'know':
    interval = 1 день
    status = 'learning'
elif rating == 'repeat':
    interval = 0 (показать сегодня через 10 минут)
    status = 'new'
elif rating == 'dont_know':
    interval = 1 день
    status = 'learning'
```

**Для карточек в статусе `learning` или `review`:**
```python
if rating == 'know':
    new_interval = round(current_interval * 2.5)
    status = 'review' if new_interval >= 7 else 'learning'

elif rating == 'repeat':
    new_interval = current_interval  # Не меняется
    # Показать через 10 минут

elif rating == 'dont_know':
    new_interval = 1  # Сброс на 1 день
    status = 'learning'
```

**Примеры прогрессии при последовательных "Знаю":**
```
Новая → 1 день → 3 дня → 8 дней → 20 дней → 50 дней → 125 дней → 313 дней
```

#### Математическая логика

**Множитель:** 2.5
- Не слишком агрессивный (не 3.0)
- Не слишком консервативный (не 2.0)
- Оптимальный баланс между нагрузкой и запоминанием

**Округление:**
```python
def calculate_next_interval(current_interval: int, rating: str) -> int:
    """
    Рассчитывает следующий интервал повторения.

    Args:
        current_interval: Текущий интервал в днях
        rating: Оценка ('know', 'repeat', 'dont_know')

    Returns:
        Новый интервал в днях
    """
    if rating == 'dont_know':
        return 1
    elif rating == 'repeat':
        return current_interval
    else:  # 'know'
        if current_interval == 0:
            return 1
        return round(current_interval * 2.5)
```

#### Время следующего повторения

**Расчет `next_review`:**
```python
from datetime import datetime, timedelta

def calculate_next_review(interval_days: int) -> datetime:
    """
    Рассчитывает дату и время следующего повторения.

    Args:
        interval_days: Интервал в днях

    Returns:
        Дата и время следующего повторения
    """
    return datetime.utcnow() + timedelta(days=interval_days)
```

**Для "Повторить":**
- Если оценка "Повторить", карточка показывается снова через 10 минут в той же сессии
- `next_review = NOW() + 10 минут`

#### Приоритет выбора карточек

**Алгоритм выбора следующей карточки:**
```python
def get_next_card(deck_id: str) -> Card | None:
    """
    Выбирает следующую карточку для изучения из колоды.

    Приоритет:
    1. Просроченные (next_review <= NOW()) - по убыванию просрочки
    2. Новые (status = 'new')
    3. Нет карточек для изучения
    """
    # 1. Ищем просроченные карточки
    due_cards = query(Card).filter(
        Card.deck_id == deck_id,
        Card.next_review <= datetime.utcnow(),
        Card.deleted == False
    ).order_by(
        Card.next_review.asc()  # Сначала самые просроченные
    ).all()

    if due_cards:
        return due_cards[0]

    # 2. Если просроченных нет - берем новые
    new_card = query(Card).filter(
        Card.deck_id == deck_id,
        Card.status == 'new',
        Card.deleted == False
    ).order_by(
        Card.created_at.asc()  # Сначала самые старые
    ).first()

    return new_card
```

**Ограничения:**
- Максимум новых карточек в день: не ограничено (пользователь сам решает)
- Сессия продолжается, пока есть карточки к повторению

### Статусы карточек

**Жизненный цикл карточки:**

#### 1. `new` - Новая
- Карточка только что создана
- Ни разу не изучалась
- `interval_days = 0`
- `next_review = NOW()`
- `reviews_count = 0`

**Переход в следующий статус:**
- После любой первой оценки → `learning`

#### 2. `learning` - Изучается
- Карточка в процессе изучения
- Интервал < 7 дней
- `interval_days = 1-6`
- Пользователь еще не закрепил материал

**Переход в следующий статус:**
- После "Знаю" с интервалом ≥ 7 дней → `review`
- После "Не знаю" → остается `learning` (сброс интервала)

#### 3. `review` - Повторение
- Карточка достигла интервала ≥ 7 дней
- Материал закреплен, но требует периодического повторения
- `interval_days >= 7`

**Возврат в предыдущий статус:**
- После "Не знаю" → `learning` (интервал сбрасывается на 1 день)

**Диаграмма переходов:**
```
┌─────────┐
│   new   │
│  (0 д)  │
└────┬────┘
     │ Любая оценка
     ▼
┌──────────┐
│ learning │  ◄───┐
│ (1-6 д)  │      │ "Не знаю"
└────┬─────┘      │
     │ "Знаю"     │
     │ (≥7 дней)  │
     ▼            │
┌──────────┐      │
│  review  │──────┘
│ (7+ дн)  │
└──────────┘
```

**Статистика по статусам:**
Для каждой колоды отслеживается:
- `new_cards_count` - количество новых карточек
- `due_cards_count` - количество просроченных карточек (требующих повторения сегодня)

#### Примечания

- Статус "Усвоена" (mastered) не используется - карточки всегда в статусе `review`
- Это позволяет продолжать повторения даже после долгих интервалов
- Максимальный интервал не ограничен (теоретически может быть > 1 года)

## Создание карточек

### Автоматическое создание

#### Создание через диалог с ботом

**Пользовательские команды:**
1. Явная команда: "Добавь слово casa в карточки"
2. Неявная команда: "Что значит casa?" → кнопка "Добавить в карточки" под ответом
3. Множественное добавление: "Добавь времена года" → создает 4 карточки (лето, зима, осень, весна)

**Процесс обработки LLM:**

#### 1. Определение намерения
```python
async def detect_add_card_intent(user_message: str) -> Intent:
    """
    Определяет, хочет ли пользователь добавить карточку.

    Ключевые слова:
    - "добавь", "создай", "сохрани"
    - "в карточки", "в колоду"
    - "запомни", "выучить"
    """
    prompt = f"""
    Analyze the user's message and determine if they want to add a word to flashcards.

    Message: "{user_message}"

    Return JSON:
    {{
      "intent": "add_card",  // or "other"
      "words": ["casa"],  // list of words to add
      "deck_name": null,  // or specific deck name
      "confidence": 0.95
    }}
    """

    response = await llm_service.chat(messages=[
        {'role': 'user', 'content': prompt}
    ], response_format={'type': 'json_object'})

    return Intent.parse_obj(json.loads(response))
```

#### 2. Проверка дубликатов

**Алгоритм:**
```python
async def check_duplicate(
    word: str,
    deck_id: str,
    language: str
) -> tuple[bool, Card | None]:
    """
    Проверяет, существует ли карточка с такой леммой.

    Этапы:
    1. Получить лемму через LLM
    2. Поиск в БД по lemma (регистронезависимо)
    3. Возврат результата
    """
    # 1. Получаем лемму (начальную форму)
    lemma = await llm_service.get_lemma(word, language)

    # 2. Ищем в БД
    existing_card = await db.query(Card).filter(
        Card.deck_id == deck_id,
        func.lower(Card.lemma) == lemma.lower(),
        Card.deleted == False
    ).first()

    return (existing_card is not None, existing_card)
```

**Определение леммы через LLM:**
```python
# Промпт: prompts/utils/get_lemma.txt
prompt = f"""
Determine the lemma (base form) of the word: "{word}" in {language}.

The lemma is:
- For nouns: singular form (with article if language requires)
- For verbs: infinitive
- For adjectives: masculine singular (if applicable)

Examples:
- Spanish: "casas" → "casa", "comí" → "comer"
- German: "Häuser" → "das Haus", "gehst" → "gehen"
- English: "houses" → "house", "went" → "go"

Respond with only the lemma, no explanation.
"""
```

**Особенности:**
- Для языков с артиклями (немецкий, греческий) лемма включает артикль
- Испанский: "casa" (без артикля)
- Немецкий: "das Haus" (с артиклем)
- Греческий: "το σπίτι" (с артиклем)

#### 3. Генерация содержимого карточки

**Вызов LLM:**
```python
async def generate_card_content(
    word: str,
    profile: LanguageProfile,
    context: str | None = None
) -> CardContent:
    """
    Генерирует полное содержимое карточки через LLM.

    Args:
        word: Слово для добавления
        profile: Языковой профиль пользователя
        context: Контекст из истории диалога (опционально)

    Returns:
        CardContent с переводом, примером и транскрипцией
    """
    prompt = render_prompt('cards/generate_card.txt', {
        'word': word,
        'language': profile.language,
        'level': profile.current_level,
        'goals': profile.goals,
        'context': context
    })

    response = await llm_service.chat(
        messages=[
            {'role': 'system', 'content': get_system_prompt(profile)},
            {'role': 'user', 'content': prompt}
        ],
        response_format={'type': 'json_object'},
        temperature=0.7
    )

    return CardContent.parse_obj(json.loads(response))
```

**Промпт для генерации (`prompts/cards/generate_card.txt`):**
```jinja2
Generate a flashcard for the word: "{{ word }}"

Requirements:
1. Provide the word in its base form (lemma)
2. Translate to Russian
3. Create an example sentence in {{ language }} (appropriate for {{ level }} level)
4. Translate the example to Russian

Consider:
- User's level: {{ level }}
- User's goals: {{ goals | join(', ') }}
- The example should be practical and memorable
{% if context %}
- Context from conversation: {{ context }}
{% endif %}

Respond in JSON format:
{
  "word": "casa",
  "lemma": "casa",
  "translation": "дом",
  "example": "Mi casa es tu casa",
  "example_translation": "Мой дом - твой дом",
  "notes": "common expression meaning 'make yourself at home'"
}
```

**Адаптация под уровень:**
- **A1-A2:** Простые примеры, базовая лексика
  - "La casa es grande" (Дом большой)
- **B1-B2:** Более сложные конструкции
  - "Compré una casa el año pasado" (Я купил дом в прошлом году)
- **C1-C2:** Идиомы, сложная грамматика
  - "Mi casa es tu casa" (Мой дом - твой дом)

#### 4. Сохранение карточки

**Финальный шаг:**
```python
async def create_card(
    word: str,
    deck_id: str,
    profile_id: str,
    user_id: str
) -> Card:
    """
    Создает карточку с полным циклом проверок.

    Этапы:
    1. Проверка лимитов
    2. Проверка дубликатов
    3. Генерация содержимого через LLM
    4. Сохранение в БД
    5. Обновление счетчиков колоды
    """
    # 1. Проверяем лимиты
    user = await get_user(user_id)
    if not user.is_premium:
        cards_count = await count_user_cards(user_id)
        if cards_count >= 200:
            raise LimitReachedError("Достигнут лимит карточек (200)")

    # 2. Проверяем дубликаты
    profile = await get_profile(profile_id)
    is_duplicate, existing = await check_duplicate(
        word, deck_id, profile.language
    )

    if is_duplicate:
        raise DuplicateCardError(f"Карточка '{existing.word}' уже существует")

    # 3. Генерируем содержимое
    content = await generate_card_content(word, profile)

    # 4. Сохраняем в БД
    card = Card(
        id=uuid4(),
        deck_id=deck_id,
        word=content.word,
        translation=content.translation,
        example=content.example,
        example_translation=content.example_translation,
        lemma=content.lemma,
        notes=content.notes,
        status='new',
        interval_days=0,
        next_review=datetime.utcnow(),
        reviews_count=0,
        created_at=datetime.utcnow()
    )

    await db.add(card)
    await db.commit()

    # 5. Обновляем счетчики (через триггер)
    # Триггер автоматически увеличит deck.cards_count и deck.new_cards_count

    return card
```

#### Множественное добавление

**Обработка списка слов:**
```python
async def create_cards_batch(
    words: list[str],
    deck_id: str,
    profile_id: str,
    user_id: str
) -> BatchResult:
    """
    Создает несколько карточек за один запрос.

    Максимум: 20 слов за раз

    Returns:
        BatchResult с списками created, duplicates, failed
    """
    if len(words) > 20:
        raise ValidationError("Максимум 20 слов за раз")

    results = BatchResult(created=[], duplicates=[], failed=[])

    for word in words:
        try:
            card = await create_card(word, deck_id, profile_id, user_id)
            results.created.append(card)
        except DuplicateCardError as e:
            results.duplicates.append({'word': word, 'error': str(e)})
        except Exception as e:
            results.failed.append({'word': word, 'error': str(e)})
            logger.error(f"Failed to create card for '{word}': {e}")

    return results
```

### Создание из изображений

#### OCR (Optical Character Recognition)

**Технологии:**
- **Tesseract OCR** - быстрое распознавание (первичное)
- **GPT-4 Vision** - улучшение точности (fallback)

> Реализовано в `app/services/media.py` (OCRService), REST `POST /api/media/ocr` и Telegram-хендлере фото (`TelegramBot._handle_photo_message`).

**Поддерживаемые языки:**
- Все основные европейские (английский, испанский, немецкий, французский, итальянский)
- Китайский, японский, корейский
- Арабский

#### Процесс обработки

**1. Получение изображения от Telegram:**
```python
async def handle_photo_message(
    update: Update,
    context: CallbackContext
):
    """
    Обрабатывает изображение от пользователя.
    """
    # Получаем самое большое изображение
    photo = update.message.photo[-1]

    # Скачиваем временно
    file = await context.bot.get_file(photo.file_id)
    image_bytes = await file.download_as_bytearray()

    # Обрабатываем
    result = await process_image_text(
        image_bytes,
        language=profile.language,
        user_id=user.id
    )

    # Удаляем временный файл автоматически (file удаляется сборщиком мусора)

    return result
```

**2. Распознавание текста:**
```python
async def process_image_text(
    image_bytes: bytes,
    language: str,
    user_id: str
) -> OCRResult:
    """
    Распознает текст с изображения комбинированным методом.

    Алгоритм:
    1. Быстрый OCR через Tesseract
    2. Если результат плохой - fallback на GPT-4 Vision
    3. Фильтрация текста по языку
    4. Возврат результата
    """
    # 1. Tesseract OCR
    tesseract_text = await extract_text_tesseract(image_bytes, language)

    # 2. Проверка качества
    if len(tesseract_text) > 50 and is_readable(tesseract_text):
        logger.info("Tesseract OCR successful")
        recognized_text = tesseract_text
    else:
        # Fallback на GPT-4 Vision
        logger.info("Falling back to GPT-4 Vision")
        image_url = await upload_temp_image(image_bytes, user_id)
        recognized_text = await extract_text_vision(image_url, language)
        await cleanup_temp_image(image_url)

    # 3. Фильтруем по языку (если мультиязычное изображение)
    filtered_text = filter_text_by_language(recognized_text, language)

    return OCRResult(
        text=filtered_text,
        confidence='high' if len(filtered_text) > 50 else 'low',
        method='tesseract' if tesseract_text else 'gpt4_vision'
    )

def extract_text_tesseract(
    image_bytes: bytes,
    language: str
) -> str:
    """
    Извлекает текст через Tesseract OCR.
    """
    import pytesseract
    from PIL import Image
    import io

    # Открываем изображение
    image = Image.open(io.BytesIO(image_bytes))

    # Предобработка (опционально)
    # - Конвертация в grayscale
    # - Увеличение контраста
    # - Удаление шумов

    # Мапим язык на Tesseract код
    lang_map = {
        'es': 'spa',
        'en': 'eng',
        'de': 'deu',
        'fr': 'fra',
        'it': 'ita',
        'ru': 'rus',
        'zh': 'chi_sim',
        'ja': 'jpn',
        'ko': 'kor',
        'ar': 'ara'
    }

    tesseract_lang = lang_map.get(language, 'eng')

    # Распознаем
    text = pytesseract.image_to_string(image, lang=tesseract_lang)

    return text.strip()

async def extract_text_vision(
    image_url: str,
    language: str
) -> str:
    """
    Извлекает текст через GPT-4 Vision API.
    Используется как fallback для плохого качества изображений.
    """
    response = await llm_service.extract_text_from_image(
        image_url,
        language
    )

    return response.strip()
```

**3. Предложение слов для добавления:**
```python
async def suggest_words_from_text(
    text: str,
    profile: LanguageProfile,
    existing_lemmas: list[str]
) -> list[WordSuggestion]:
    """
    Анализирует текст и предлагает слова для добавления в карточки.

    Критерии отбора:
    - Частотность в языке
    - Соответствие уровню пользователя
    - Практическая полезность для целей обучения
    - Отсутствие в существующих карточках

    Максимум: 10 слов
    """
    prompt = render_prompt('cards/suggest_words.txt', {
        'text': text,
        'language': profile.language,
        'level': profile.current_level,
        'goals': profile.goals,
        'existing_lemmas': existing_lemmas[:50]  # Последние 50 для контекста
    })

    response = await llm_service.chat(
        messages=[
            {'role': 'system', 'content': get_system_prompt(profile)},
            {'role': 'user', 'content': prompt}
        ],
        response_format={'type': 'json_object'},
        temperature=0.8
    )

    suggestions = json.loads(response)['suggestions']

    return [WordSuggestion(**s) for s in suggestions[:10]]
```

**4. Отображение в боте:**
```python
async def send_ocr_result_with_suggestions(
    update: Update,
    ocr_result: OCRResult,
    suggestions: list[WordSuggestion]
):
    """
    Отправляет распознанный текст и кнопки для добавления слов.
    """
    message = f"📄 Распознанный текст:\n\n{ocr_result.text}\n\n"

    if suggestions:
        message += "💡 Предлагаю добавить в карточки:"

    # Создаем inline кнопки для каждого слова
    keyboard = []
    for suggestion in suggestions:
        keyboard.append([
            InlineKeyboardButton(
                text=f"➕ {suggestion.word}",
                callback_data=f"add_card:{suggestion.word}"
            )
        ])

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        message,
        reply_markup=reply_markup,
        parse_mode='HTML'
    )
```

### Создание из голоса

#### Speech-to-Text (STT)

**Технология:** OpenAI Whisper API

> Реализация: `app/services/speech_to_text.py` + хендлер `TelegramBot._handle_voice_message`. Лимиты на длину/размер настраиваются через `VOICE_*` переменные окружения.

**Поддерживаемые языки:** 50+ языков с автоопределением

**Характеристики:**
- Максимальная длина: 2 минуты (ограничение Telegram)
- Формат: OGG (Telegram voice messages)
- Качество: высокое (модель large-v3)

#### Процесс обработки

**1. Получение голосового сообщения:**
```python
async def handle_voice_message(
    update: Update,
    context: CallbackContext
):
    """
    Обрабатывает голосовое сообщение.
    """
    voice = update.message.voice

    # Проверяем длительность (макс 2 минуты = 120 секунд)
    if voice.duration > 120:
        await update.message.reply_text(
            "Голосовое сообщение слишком длинное. "
            "Максимум 2 минуты. Попробуйте отправить более короткое."
        )
        return

    # Скачиваем
    file = await context.bot.get_file(voice.file_id)
    audio_bytes = await file.download_as_bytearray()

    # Транскрибируем
    transcript, detected_language = await transcribe_voice(
        audio_bytes,
        expected_language=profile.language
    )

    # Проверяем соответствие языка
    if detected_language != profile.language:
        await update.message.reply_text(
            f"⚠️ Обнаружен язык: {detected_language}, "
            f"ожидался: {profile.language}\n\n"
            f"Распознано: {transcript}"
        )
    else:
        await update.message.reply_text(
            f"🎤 Распознано: {transcript}"
        )

    # Обрабатываем как текстовое сообщение
    await process_user_message(
        user=user,
        profile=profile,
        message=transcript,
        source='voice'
    )
```

**2. Транскрипция через Whisper:**
```python
async def transcribe_voice(
    audio_bytes: bytes,
    expected_language: str | None = None
) -> tuple[str, str]:
    """
    Транскрибирует голосовое сообщение через Whisper API.

    Args:
        audio_bytes: Аудио в формате OGG
        expected_language: Ожидаемый язык (ISO 639-1)

    Returns:
        (transcript, detected_language)
    """
    # Сохраняем во временный файл (Whisper требует file-like object)
    with tempfile.NamedTemporaryFile(suffix='.ogg', delete=False) as temp_file:
        temp_file.write(audio_bytes)
        temp_file_path = temp_file.name

    try:
        # Транскрибируем
        with open(temp_file_path, 'rb') as audio:
            response = await openai_client.audio.transcriptions.create(
                model="whisper-1",
                file=audio,
                language=expected_language,  # Подсказка для Whisper
                response_format="verbose_json"  # Включает detected_language
            )

        transcript = response.text
        detected_language = response.language

        logger.info(
            f"Transcribed {len(transcript)} chars, "
            f"language: {detected_language}"
        )

        return transcript, detected_language

    finally:
        # Удаляем временный файл
        os.unlink(temp_file_path)
```

**3. Создание карточки из голосового сообщения:**

После транскрипции текст обрабатывается стандартным образом:
- Определяется намерение ("добавь слово X")
- Проверяются дубликаты
- Генерируется содержимое через LLM
- Сохраняется карточка

**Особенности:**
- Голосовое сообщение распознается полностью
- Можно сказать: "Добавь слово casa в карточки"
- Можно просто сказать слово: "casa" → бот спросит, что с ним делать

### Ручное создание

#### Через Mini App

**Интерфейс создания карточки:**

**1. Форма добавления:**
```typescript
interface CardCreationForm {
  // Обязательные поля
  words: string[];  // Одно или несколько слов

  // Опциональные поля
  deck_id?: string;  // Если не указано - активная колода

  // Форматы ввода:
  // - Одно слово: "casa"
  // - Несколько слов через запятую: "casa, perro, gato"
  // - Несколько слов с новой строки:
  //   casa
  //   perro
  //   gato
}
```

**2. UI компонент:**
```tsx
// components/AddCardForm.tsx
const AddCardForm: React.FC = () => {
  const [words, setWords] = useState<string>('');
  const [deckId, setDeckId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async () => {
    setLoading(true);

    // Парсим слова
    const wordsList = parseWordsList(words);

    try {
      const result = await api.cards.createBatch({
        deck_id: deckId || activeDecкId,
        words: wordsList
      });

      // Показываем результат
      showToast(`✅ Добавлено: ${result.created.length}`);

      if (result.duplicates.length > 0) {
        showWarning(`⚠️ Дубликаты: ${result.duplicates.length}`);
      }

      if (result.failed.length > 0) {
        showError(`❌ Ошибки: ${result.failed.length}`);
      }

      // Очищаем форму
      setWords('');

    } catch (error) {
      showError('Не удалось добавить карточки');
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <textarea
        value={words}
        onChange={(e) => setWords(e.target.value)}
        placeholder="Введите слова (по одному на строке или через запятую)"
        rows={5}
      />

      <select
        value={deckId || ''}
        onChange={(e) => setDeckId(e.target.value || null)}
      >
        <option value="">Активная колода</option>
        {decks.map(deck => (
          <option key={deck.id} value={deck.id}>
            {deck.name}
          </option>
        ))}
      </select>

      <button type="submit" disabled={loading || !words.trim()}>
        {loading ? 'Добавление...' : 'Добавить'}
      </button>
    </form>
  );
};

function parseWordsList(input: string): string[] {
  // Поддерживаем два формата:
  // 1. Через запятую: "casa, perro, gato"
  // 2. С новой строки:
  //    casa
  //    perro
  //    gato

  // Сначала пробуем разделить по новой строке
  let words = input.split('\n').map(w => w.trim()).filter(Boolean);

  // Если только одна строка - пробуем разделить по запятой
  if (words.length === 1 && words[0].includes(',')) {
    words = words[0].split(',').map(w => w.trim()).filter(Boolean);
  }

  return words;
}
```

**3. Batch результат:**
```tsx
// Отображение результата batch создания
const BatchResultView: React.FC<{ result: BatchResult }> = ({ result }) => {
  return (
    <div className="batch-result">
      {result.created.length > 0 && (
        <div className="success">
          <h4>✅ Добавлено: {result.created.length}</h4>
          <ul>
            {result.created.map(card => (
              <li key={card.id}>
                {card.word} - {card.translation}
              </li>
            ))}
          </ul>
        </div>
      )}

      {result.duplicates.length > 0 && (
        <div className="warning">
          <h4>⚠️ Дубликаты: {result.duplicates.length}</h4>
          <ul>
            {result.duplicates.map((dup, i) => (
              <li key={i}>
                {dup.word}: {dup.error}
              </li>
            ))}
          </ul>
        </div>
      )}

      {result.failed.length > 0 && (
        <div className="error">
          <h4>❌ Ошибки: {result.failed.length}</h4>
          <ul>
            {result.failed.map((fail, i) => (
              <li key={i}>
                {fail.word}: {fail.error}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};
```

#### Через бот

**Команда `/add_card`:**
```python
async def add_card_command(update: Update, context: CallbackContext):
    """
    Команда /add_card для добавления карточки.

    Использование:
    /add_card casa
    /add_card casa perro gato
    """
    if not context.args:
        await update.message.reply_text(
            "Использование: /add_card <слово1> [слово2] ...\n"
            "Пример: /add_card casa\n"
            "Или: /add_card casa perro gato"
        )
        return

    words = context.args
    user = await get_user(update.effective_user.id)
    profile = await get_active_profile(user.id)
    active_deck = await get_active_deck(profile.id)

    # Создаем карточки
    result = await create_cards_batch(
        words=words,
        deck_id=active_deck.id,
        profile_id=profile.id,
        user_id=user.id
    )

    # Формируем ответ
    message = ""

    if result.created:
        message += f"✅ Добавлено карточек: {len(result.created)}\n\n"
        for card in result.created:
            message += f"📝 {card.word} - {card.translation}\n"
            message += f"   💬 {card.example}\n\n"

    if result.duplicates:
        message += f"⚠️ Дубликаты ({len(result.duplicates)}):\n"
        for dup in result.duplicates:
            message += f"   • {dup['word']}\n"

    if result.failed:
        message += f"❌ Ошибки ({len(result.failed)}):\n"
        for fail in result.failed:
            message += f"   • {fail['word']}: {fail['error']}\n"

    await update.message.reply_text(message)
```

## Организация карточек

### Колоды (Decks)

#### Концепция

**Колода (Deck)** - это контейнер для группировки карточек по теме, уровню или цели обучения.

**Характеристики:**
- Каждый пользователь имеет как минимум 1 колоду
- Карточка принадлежит только одной колоде
- Одна колода может быть активной (для быстрого доступа)
- Колоды могут быть личными или групповыми (shared)

#### Структура колоды

```python
class Deck:
    id: UUID
    profile_id: UUID  # Принадлежность к языковому профилю
    name: str  # Название колоды
    description: str | None  # Описание (опционально)
    is_active: bool  # Активная колода
    is_group: bool  # Групповая колода (из группы)
    owner_id: UUID | None  # Владелец (для групповых)
    cards_count: int  # Всего карточек
    new_cards_count: int  # Новых карточек
    due_cards_count: int  # Просроченных карточек
    created_at: datetime
    updated_at: datetime
```

#### Автоматическое создание колоды

**При создании профиля:**
```python
async def create_profile(
    user_id: str,
    language: str,
    current_level: str,
    ...
) -> LanguageProfile:
    """
    Создает языковой профиль с дефолтной колодой.
    """
    # 1. Создаем профиль
    profile = LanguageProfile(
        id=uuid4(),
        user_id=user_id,
        language=language,
        current_level=current_level,
        ...
    )

    await db.add(profile)

    # 2. Создаем дефолтную колоду
    default_deck = Deck(
        id=uuid4(),
        profile_id=profile.id,
        name=f"Мои слова ({language_name})",
        is_active=True,
        is_group=False,
        cards_count=0,
        new_cards_count=0,
        due_cards_count=0,
        created_at=datetime.utcnow()
    )

    await db.add(default_deck)
    await db.commit()

    return profile
```

#### Управление колодами

**Создание новой колоды:**
```python
async def create_deck(
    profile_id: str,
    name: str,
    description: str | None = None
) -> Deck:
    """
    Создает новую колоду для профиля.
    """
    deck = Deck(
        id=uuid4(),
        profile_id=profile_id,
        name=name,
        description=description,
        is_active=False,  # Не активная по умолчанию
        is_group=False,
        cards_count=0,
        new_cards_count=0,
        due_cards_count=0,
        created_at=datetime.utcnow()
    )

    await db.add(deck)
    await db.commit()

    return deck
```

**Активация колоды:**
```python
async def activate_deck(deck_id: str, profile_id: str):
    """
    Устанавливает колоду как активную.
    Деактивирует предыдущую активную колоду.
    """
    # 1. Деактивируем все колоды профиля
    await db.execute(
        update(Deck)
        .where(Deck.profile_id == profile_id)
        .values(is_active=False)
    )

    # 2. Активируем выбранную
    await db.execute(
        update(Deck)
        .where(Deck.id == deck_id)
        .values(is_active=True)
    )

    await db.commit()
```

**Примеры группировки:**
- **По теме:** "Еда и напитки", "Путешествия", "Работа"
- **По уровню:** "A1-A2", "B1-B2", "Продвинутый"
- **По источнику:** "Из учебника", "Из фильмов", "Разговорные фразы"
- **По частоте:** "Топ 1000", "Редкие слова"

#### Удаление колоды

**Soft delete:**
```python
async def delete_deck(deck_id: str, profile_id: str):
    """
    Удаляет колоду (soft delete).

    Ограничения:
    - Нельзя удалить единственную колоду
    - Нельзя удалить групповую колоду
    """
    # 1. Проверяем, что это не единственная колода
    decks_count = await db.query(Deck).filter(
        Deck.profile_id == profile_id,
        Deck.deleted == False
    ).count()

    if decks_count <= 1:
        raise BusinessLogicError("Нельзя удалить последнюю колоду")

    # 2. Проверяем, что это не групповая колода
    deck = await db.query(Deck).filter(Deck.id == deck_id).first()

    if deck.is_group:
        raise BusinessLogicError("Нельзя удалить групповую колоду")

    # 3. Soft delete колоды и всех ее карточек
    await db.execute(
        update(Deck)
        .where(Deck.id == deck_id)
        .values(deleted=True, deleted_at=datetime.utcnow())
    )

    await db.execute(
        update(Card)
        .where(Card.deck_id == deck_id)
        .values(deleted=True, deleted_at=datetime.utcnow())
    )

    await db.commit()

    # 4. Если удаленная колода была активной - активируем первую доступную
    if deck.is_active:
        first_deck = await db.query(Deck).filter(
            Deck.profile_id == profile_id,
            Deck.deleted == False
        ).first()

        if first_deck:
            await activate_deck(first_deck.id, profile_id)
```

### Теги и фильтрация

#### Система тегов (Будущая функция)

**Примечание:** В текущей версии (MVP) система тегов не реализована. Вместо этого используются колоды для группировки.

**Планируемая реализация:**

```python
# Будущая структура (после MVP)
class Tag:
    id: UUID
    profile_id: UUID
    name: str  # Название тега
    color: str | None  # Цвет (hex)
    created_at: datetime

class CardTag:
    card_id: UUID
    tag_id: UUID
    created_at: datetime
```

**Примеры использования тегов:**
- Грамматические категории: `#глагол`, `#существительное`, `#прилагательное`
- Тематика: `#еда`, `#путешествия`, `#работа`
- Сложность: `#сложное`, `#легкое`, `#путаюсь`
- Источник: `#из_фильма`, `#из_книги`, `#от_преподавателя`

#### Фильтрация карточек

**Текущие фильтры (MVP):**

**1. По колоде:**
```python
GET /api/cards?deck_id=<uuid>
```

**2. По статусу:**
```python
GET /api/cards?deck_id=<uuid>&status=new
GET /api/cards?deck_id=<uuid>&status=learning
GET /api/cards?deck_id=<uuid>&status=review
```

**3. По поиску:**
```python
GET /api/cards?deck_id=<uuid>&search=casa
# Поиск по word, translation, example
```

**Реализация поиска:**
```python
async def search_cards(
    deck_id: str,
    search_query: str,
    limit: int = 20,
    offset: int = 0
) -> list[Card]:
    """
    Поиск карточек по слову, переводу или примеру.
    """
    query = db.query(Card).filter(
        Card.deck_id == deck_id,
        Card.deleted == False,
        or_(
            Card.word.ilike(f'%{search_query}%'),
            Card.translation.ilike(f'%{search_query}%'),
            Card.example.ilike(f'%{search_query}%')
        )
    ).order_by(
        Card.created_at.desc()
    ).limit(limit).offset(offset)

    return await query.all()
```

### Шаринг карточек в группах

#### Концепция групп

**Группа** - это сообщество пользователей, которые делятся учебными материалами (колодами и темами).

**Роли в группе:**
- **Owner** (владелец) - создатель группы, может управлять участниками и материалами
- **Member** (участник) - может использовать материалы группы, но не может редактировать

#### Групповые колоды

**Как работает:**
1. Владелец группы создает колоду (или использует существующую)
2. Владелец добавляет колоду в материалы группы
3. Все участники группы получают доступ к этой колоде
4. Групповая колода отображается в списке колод участников (с пометкой `is_group=true`)
5. Участники могут изучать карточки из групповой колоды, но не могут их редактировать или удалять

**Добавление колоды в группу:**
```python
async def share_deck_to_group(
    deck_id: str,
    group_id: str,
    owner_id: str
):
    """
    Добавляет колоду в материалы группы.

    Только владелец группы может добавлять материалы.
    """
    # 1. Проверяем права (владелец группы)
    group = await db.query(Group).filter(Group.id == group_id).first()

    if group.owner_id != owner_id:
        raise PermissionError("Только владелец может добавлять материалы")

    # 2. Проверяем, что колода принадлежит владельцу
    deck = await db.query(Deck).filter(Deck.id == deck_id).first()

    if deck.profile_id not in await get_user_profiles(owner_id):
        raise PermissionError("Колода не принадлежит владельцу")

    # 3. Создаем связь группа-колода
    group_material = GroupMaterial(
        id=uuid4(),
        group_id=group_id,
        material_type='deck',
        material_id=deck_id,
        owner_id=owner_id,
        created_at=datetime.utcnow()
    )

    await db.add(group_material)
    await db.commit()

    # 4. Отправляем уведомления участникам (опционально)
    await notify_group_members(
        group_id,
        f"Добавлен новый материал: {deck.name}"
    )
```

**Получение групповых колод:**
```python
async def get_decks_with_group(
    profile_id: str,
    include_group: bool = True
) -> list[Deck]:
    """
    Получает колоды профиля, включая групповые.
    """
    # 1. Личные колоды
    own_decks = await db.query(Deck).filter(
        Deck.profile_id == profile_id,
        Deck.deleted == False
    ).all()

    if not include_group:
        return own_decks

    # 2. Групповые колоды
    user = await get_user_by_profile(profile_id)

    # Получаем группы, в которых пользователь участвует
    user_groups = await db.query(GroupMember).filter(
        GroupMember.user_id == user.id
    ).all()

    group_decks = []

    for membership in user_groups:
        # Получаем материалы группы
        materials = await db.query(GroupMaterial).filter(
            GroupMaterial.group_id == membership.group_id,
            GroupMaterial.material_type == 'deck'
        ).all()

        for material in materials:
            deck = await db.query(Deck).filter(
                Deck.id == material.material_id
            ).first()

            if deck and not deck.deleted:
                # Помечаем как групповую
                deck.is_group = True
                deck.owner_id = material.owner_id
                deck.owner_name = await get_user_name(material.owner_id)
                group_decks.append(deck)

    return own_decks + group_decks
```

#### Прогресс по групповым материалам

**Независимый прогресс:**
- Каждый участник имеет свой собственный прогресс по карточкам
- Интервалы повторений, оценки и статистика хранятся отдельно для каждого участника
- Владелец группы может видеть агрегированный прогресс участников

**Структура данных:**
```python
# Таблица card_reviews хранит индивидуальный прогресс
class CardReview:
    id: UUID
    card_id: UUID  # Карточка из групповой колоды
    user_id: UUID  # Конкретный участник
    profile_id: UUID  # Профиль участника
    rating: str  # 'know', 'repeat', 'dont_know'
    interval_before: int
    interval_after: int
    created_at: datetime
```

**Просмотр прогресса участников (для владельца):**
```python
async def get_member_progress(
    group_id: str,
    user_id: str,
    owner_id: str
) -> MemberProgress:
    """
    Получает прогресс участника по материалам группы.

    Только для владельца группы.
    """
    # 1. Проверяем права
    group = await db.query(Group).filter(Group.id == group_id).first()

    if group.owner_id != owner_id:
        raise PermissionError("Только владелец может просматривать прогресс")

    # 2. Получаем материалы группы (колоды)
    materials = await db.query(GroupMaterial).filter(
        GroupMaterial.group_id == group_id,
        GroupMaterial.material_type == 'deck'
    ).all()

    decks_progress = []

    for material in materials:
        deck = await db.query(Deck).filter(
            Deck.id == material.material_id
        ).first()

        # Получаем все карточки колоды
        cards = await db.query(Card).filter(
            Card.deck_id == deck.id,
            Card.deleted == False
        ).all()

        # Получаем прогресс участника по этим карточкам
        reviews = await db.query(CardReview).filter(
            CardReview.card_id.in_([c.id for c in cards]),
            CardReview.user_id == user_id
        ).all()

        # Статистика
        total_cards = len(cards)
        studied_cards = len(set(r.card_id for r in reviews))

        stats = {
            'know': sum(1 for r in reviews if r.rating == 'know'),
            'repeat': sum(1 for r in reviews if r.rating == 'repeat'),
            'dont_know': sum(1 for r in reviews if r.rating == 'dont_know')
        }

        decks_progress.append({
            'deck_id': deck.id,
            'deck_name': deck.name,
            'total_cards': total_cards,
            'studied_cards': studied_cards,
            'progress': studied_cards / total_cards if total_cards > 0 else 0,
            'stats': stats,
            'last_activity': max((r.created_at for r in reviews), default=None)
        })

    return MemberProgress(
        user_id=user_id,
        user_name=await get_user_name(user_id),
        decks=decks_progress
    )
```

**API Endpoint:**
```
GET /api/groups/{group_id}/members/{user_id}/progress
```

**Использование:**
- Преподаватель может отслеживать прогресс студентов
- Владелец группы может видеть активность участников
- Помогает выявить участников, которым нужна помощь

## Процесс изучения

### Режимы повторения

#### 1. Через Telegram бота

**Команда `/study`:**
```python
async def study_command(update: Update, context: CallbackContext):
    """
    Начинает сессию изучения карточек в боте.
    """
    user = await get_user(update.effective_user.id)
    profile = await get_active_profile(user.id)
    active_deck = await get_active_deck(profile.id)

    # Получаем следующую карточку
    card = await get_next_card(active_deck.id)

    if not card:
        await update.message.reply_text(
            "🎉 Отличная работа!\n\n"
            "У вас нет карточек для повторения сегодня.\n"
            "Возвращайтесь завтра!"
        )
        return

    # Отображаем карточку
    await show_card(update, card, side='front')
```

**Отображение карточки:**
```python
async def show_card(
    update: Update,
    card: Card,
    side: Literal['front', 'back']
):
    """
    Отображает карточку пользователю.

    Side:
    - 'front': показываем слово на изучаемом языке
    - 'back': показываем перевод и пример
    """
    if side == 'front':
        # Показываем слово
        message = f"🇪🇸 {card.word}\n\n"
        message += f"📖 {card.example}"

        # Кнопка "Показать перевод"
        keyboard = [[
            InlineKeyboardButton(
                text="Показать перевод",
                callback_data=f"show_back:{card.id}"
            )
        ]]

        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            message,
            reply_markup=reply_markup
        )

    else:  # 'back'
        # Показываем перевод и пример
        message = f"🇪🇸 {card.word}\n"
        message += f"🇷🇺 {card.translation}\n\n"
        message += f"📖 {card.example}\n"
        message += f"   {card.example_translation}\n\n"

        if card.notes:
            message += f"💡 {card.notes}\n\n"

        message += "Насколько хорошо вы помните это слово?"

        # Кнопки для оценки
        keyboard = [
            [
                InlineKeyboardButton("❌ Не знаю", callback_data=f"rate:{card.id}:dont_know"),
                InlineKeyboardButton("🔁 Повторить", callback_data=f"rate:{card.id}:repeat"),
                InlineKeyboardButton("✅ Знаю", callback_data=f"rate:{card.id}:know")
            ]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.callback_query.edit_message_text(
            message,
            reply_markup=reply_markup
        )
```

**Обработка оценки:**
```python
async def handle_rating(
    update: Update,
    context: CallbackContext
):
    """
    Обрабатывает оценку карточки пользователем.
    """
    # Парсим callback_data: "rate:<card_id>:<rating>"
    data = update.callback_query.data.split(':')
    card_id = data[1]
    rating = data[2]  # 'know', 'repeat', 'dont_know'

    user = await get_user(update.effective_user.id)
    profile = await get_active_profile(user.id)

    # Обновляем карточку
    updated_card = await rate_card(
        card_id=card_id,
        user_id=user.id,
        profile_id=profile.id,
        rating=rating
    )

    # Показываем результат
    if rating == 'know':
        emoji = '✅'
        text = 'Отлично!'
        next_review_text = f"Следующее повторение через {updated_card.interval_days} дн."
    elif rating == 'repeat':
        emoji = '🔁'
        text = 'Хорошо, повторим еще раз'
        next_review_text = 'Покажем снова через 10 минут'
    else:  # dont_know
        emoji = '❌'
        text = 'Ничего страшного! Повторим завтра'
        next_review_text = 'Следующее повторение завтра'

    await update.callback_query.answer(f"{emoji} {text}")

    # Получаем следующую карточку
    active_deck = await get_active_deck(profile.id)
    next_card = await get_next_card(active_deck.id)

    if next_card:
        # Показываем следующую карточку
        await show_card(update, next_card, side='front')
    else:
        # Сессия завершена
        stats = await get_session_stats(user.id, profile.id)

        message = (
            f"🎉 Сессия завершена!\n\n"
            f"📊 Статистика:\n"
            f"✅ Знаю: {stats['know']}\n"
            f"🔁 Повторить: {stats['repeat']}\n"
            f"❌ Не знаю: {stats['dont_know']}\n\n"
            f"{next_review_text}"
        )

        await update.callback_query.edit_message_text(message)
```

#### 2. Через Mini App

**Интерфейс изучения:**

**Компонент карточки:**
```tsx
// components/FlashcardView.tsx
const FlashcardView: React.FC<{ card: Card }> = ({ card }) => {
  const [flipped, setFlipped] = useState(false);

  const handleFlip = () => {
    setFlipped(!flipped);
  };

  const handleRate = async (rating: 'know' | 'repeat' | 'dont_know') => {
    await api.cards.rate(card.id, rating);

    // Получаем следующую карточку
    const nextCard = await api.cards.getNext(deckId);

    if (nextCard) {
      // Показываем следующую
      setCard(nextCard);
      setFlipped(false);
    } else {
      // Сессия завершена
      showSessionComplete();
    }
  };

  return (
    <div className="flashcard-container">
      <div
        className={`flashcard ${flipped ? 'flipped' : ''}`}
        onClick={handleFlip}
      >
        {!flipped ? (
          // Лицевая сторона
          <div className="front">
            <h2 className="word">{card.word}</h2>
            <p className="example">{card.example}</p>
            <p className="hint">Нажмите, чтобы увидеть перевод</p>
          </div>
        ) : (
          // Обратная сторона
          <div className="back">
            <h2 className="word">{card.word}</h2>
            <h3 className="translation">{card.translation}</h3>
            <div className="example-block">
              <p className="example">{card.example}</p>
              <p className="example-translation">{card.example_translation}</p>
            </div>
            {card.notes && (
              <p className="notes">💡 {card.notes}</p>
            )}
          </div>
        )}
      </div>

      {flipped && (
        <div className="rating-buttons">
          <button
            className="btn-dont-know"
            onClick={() => handleRate('dont_know')}
          >
            ❌ Не знаю
          </button>
          <button
            className="btn-repeat"
            onClick={() => handleRate('repeat')}
          >
            🔁 Повторить
          </button>
          <button
            className="btn-know"
            onClick={() => handleRate('know')}
          >
            ✅ Знаю
          </button>
        </div>
      )}
    </div>
  );
};
```

**Сессия изучения:**
```tsx
// screens/StudySession.tsx
const StudySession: React.FC = () => {
  const [deck, setDeck] = useState<Deck | null>(null);
  const [card, setCard] = useState<Card | null>(null);
  const [sessionStats, setSessionStats] = useState({
    know: 0,
    repeat: 0,
    dont_know: 0,
    total: 0
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadNextCard();
  }, []);

  const loadNextCard = async () => {
    setLoading(true);

    try {
      const nextCard = await api.cards.getNext(deckId);

      if (nextCard) {
        setCard(nextCard);
      } else {
        // Нет карточек для изучения
        showSessionComplete();
      }
    } catch (error) {
      showError('Не удалось загрузить карточку');
    } finally {
      setLoading(false);
    }
  };

  const handleRate = (rating: CardRating) => {
    // Обновляем статистику
    setSessionStats(prev => ({
      ...prev,
      [rating]: prev[rating] + 1,
      total: prev.total + 1
    }));

    // Загружаем следующую карточку
    loadNextCard();
  };

  if (loading) {
    return <LoadingSpinner />;
  }

  if (!card) {
    return (
      <SessionComplete
        stats={sessionStats}
        onRestart={() => loadNextCard()}
      />
    );
  }

  return (
    <div className="study-session">
      <SessionHeader deck={deck} stats={sessionStats} />
      <FlashcardView card={card} onRate={handleRate} />
      <SessionProgress deck={deck} />
    </div>
  );
};
```

#### 3. Быстрое повторение (Quick Review)

**В боте:**
```
/quick_review - быстро повторить 10 карточек
```

**Особенности:**
- Показывает только просроченные карточки
- Максимум 10 карточек за сессию
- Подходит для коротких перерывов

**В Mini App:**
- Кнопка "Быстрое повторение" на главном экране
- Показывает счетчик оставшихся карточек
- Можно прервать в любой момент

#### 4. Режим "Учу новые" (Learn New)

**Специальный режим для новых карточек:**
```python
async def learn_new_cards(deck_id: str, limit: int = 10) -> list[Card]:
    """
    Возвращает новые карточки для изучения.

    Лимит: 10 новых карточек за сессию (по умолчанию)
    """
    return await db.query(Card).filter(
        Card.deck_id == deck_id,
        Card.status == 'new',
        Card.deleted == False
    ).order_by(
        Card.created_at.asc()  # Сначала самые старые
    ).limit(limit).all()
```

**Стратегия:**
- Пользователь выбирает, сколько новых карточек хочет выучить
- Новые карточки показываются в порядке добавления
- После оценки новая карточка переходит в статус `learning`

### Прогресс и статистика

#### Метрики для карточек

**На уровне карточки:**
```python
class Card:
    # ... основные поля
    status: str  # 'new', 'learning', 'review'
    interval_days: int  # Текущий интервал
    next_review: datetime  # Следующее повторение
    reviews_count: int  # Сколько раз повторялась
    last_rating: str | None  # Последняя оценка
```

**На уровне колоды:**
```python
class Deck:
    # ... основные поля
    cards_count: int  # Всего карточек
    new_cards_count: int  # Новых
    due_cards_count: int  # К повторению сегодня
```

**Вычисляемые метрики:**
```python
async def get_deck_stats(deck_id: str) -> DeckStats:
    """
    Получает статистику колоды.
    """
    cards = await db.query(Card).filter(
        Card.deck_id == deck_id,
        Card.deleted == False
    ).all()

    # Подсчитываем по статусам
    new_count = sum(1 for c in cards if c.status == 'new')
    learning_count = sum(1 for c in cards if c.status == 'learning')
    review_count = sum(1 for c in cards if c.status == 'review')

    # Подсчитываем просроченные (due)
    now = datetime.utcnow()
    due_count = sum(1 for c in cards if c.next_review <= now and c.status != 'new')

    # Подсчитываем по последней оценке
    know_count = sum(1 for c in cards if c.last_rating == 'know')
    repeat_count = sum(1 for c in cards if c.last_rating == 'repeat')
    dont_know_count = sum(1 for c in cards if c.last_rating == 'dont_know')

    return DeckStats(
        total=len(cards),
        new=new_count,
        learning=learning_count,
        review=review_count,
        due=due_count,
        know=know_count,
        repeat=repeat_count,
        dont_know=dont_know_count
    )
```

#### Метрики для пользователя

**Streak (серия дней):**
```python
async def calculate_streak(user_id: str, profile_id: str) -> StreakInfo:
    """
    Рассчитывает streak (серию дней подряд).

    Условие streak: хотя бы 1 действие в день
    Действия: изучение карточки, упражнение, сообщение LLM
    """
    # Получаем даты активности
    activity_dates = await db.query(
        func.date(Activity.created_at).label('date')
    ).filter(
        Activity.user_id == user_id,
        Activity.profile_id == profile_id
    ).distinct().order_by(
        func.date(Activity.created_at).desc()
    ).all()

    if not activity_dates:
        return StreakInfo(current=0, best=0, total_days=0)

    # Рассчитываем текущий streak
    current_streak = 0
    today = datetime.utcnow().date()
    expected_date = today

    for activity_date in activity_dates:
        date = activity_date.date

        if date == expected_date:
            current_streak += 1
            expected_date = expected_date - timedelta(days=1)
        elif date < expected_date:
            # Пропуск дня - streak прерван
            break

    # Рассчитываем лучший streak (требует более сложной логики)
    best_streak = await calculate_best_streak(activity_dates)

    return StreakInfo(
        current=current_streak,
        best=best_streak,
        total_days=len(activity_dates)
    )
```

**Прогресс по уровню:**
```python
async def get_level_progress(profile_id: str) -> LevelProgress:
    """
    Оценивает прогресс к следующему уровню.

    Критерии:
    - Количество карточек в статусе 'review'
    - Точность в упражнениях
    - Время изучения
    """
    profile = await db.query(LanguageProfile).filter(
        LanguageProfile.id == profile_id
    ).first()

    # Карточки
    cards_stats = await get_profile_cards_stats(profile_id)

    # Упражнения
    exercises_stats = await get_profile_exercises_stats(profile_id)

    # Примерные критерии для перехода на следующий уровень:
    # A1 → A2: 300 карточек в review + 80% accuracy
    # A2 → B1: 600 карточек в review + 85% accuracy
    # B1 → B2: 1000 карточек в review + 90% accuracy

    target_cards = {
        'A1': 300,
        'A2': 600,
        'B1': 1000,
        'B2': 1500,
        'C1': 2000
    }.get(profile.current_level, 2500)

    target_accuracy = {
        'A1': 0.80,
        'A2': 0.85,
        'B1': 0.90,
        'B2': 0.92,
        'C1': 0.95
    }.get(profile.current_level, 0.95)

    # Прогресс
    cards_progress = min(cards_stats.review_count / target_cards, 1.0)
    accuracy_progress = min(exercises_stats.accuracy / target_accuracy, 1.0)

    # Общий прогресс (взвешенное среднее)
    overall_progress = 0.6 * cards_progress + 0.4 * accuracy_progress

    return LevelProgress(
        current_level=profile.current_level,
        target_level=profile.target_level,
        progress=overall_progress,
        cards_mastered=cards_stats.review_count,
        target_cards=target_cards,
        exercises_accuracy=exercises_stats.accuracy,
        target_accuracy=target_accuracy
    )
```

**Статистика за период:**
```python
async def get_user_stats(
    user_id: str,
    profile_id: str,
    period: Literal['week', 'month', '3months', 'year', 'all'] = 'month'
) -> UserStats:
    """
    Получает агрегированную статистику пользователя.
    """
    # Определяем временной диапазон
    now = datetime.utcnow()
    start_date = {
        'week': now - timedelta(days=7),
        'month': now - timedelta(days=30),
        '3months': now - timedelta(days=90),
        'year': now - timedelta(days=365),
        'all': datetime(1970, 1, 1)
    }[period]

    # Карточки
    cards_reviews = await db.query(CardReview).filter(
        CardReview.user_id == user_id,
        CardReview.profile_id == profile_id,
        CardReview.created_at >= start_date
    ).all()

    # Упражнения
    exercises = await db.query(ExerciseAttempt).filter(
        ExerciseAttempt.user_id == user_id,
        ExerciseAttempt.profile_id == profile_id,
        ExerciseAttempt.created_at >= start_date
    ).all()

    # Подсчитываем
    cards_stats = {
        'know': sum(1 for r in cards_reviews if r.rating == 'know'),
        'repeat': sum(1 for r in cards_reviews if r.rating == 'repeat'),
        'dont_know': sum(1 for r in cards_reviews if r.rating == 'dont_know')
    }

    exercises_stats = {
        'correct': sum(1 for e in exercises if e.result == 'correct'),
        'partial': sum(1 for e in exercises if e.result == 'partial'),
        'incorrect': sum(1 for e in exercises if e.result == 'incorrect')
    }

    accuracy = (
        exercises_stats['correct'] / len(exercises)
        if exercises else 0
    )

    # Время изучения
    time_minutes = sum(
        (e.duration_seconds or 0) / 60
        for e in exercises
    )

    # Активность по дням
    activity_by_day = await get_activity_calendar(
        user_id, profile_id, start_date, now
    )

    # Streak
    streak = await calculate_streak(user_id, profile_id)

    return UserStats(
        profile_id=profile_id,
        period=period,
        streak=streak,
        cards=CardStats(
            total=len(cards_reviews),
            stats=cards_stats
        ),
        exercises=ExerciseStats(
            total=len(exercises),
            stats=exercises_stats,
            accuracy=accuracy
        ),
        time=TimeStats(
            total_minutes=int(time_minutes),
            average_per_day=int(time_minutes / max(streak.total_days, 1))
        ),
        activity=activity_by_day
    )
```

**API Endpoints:**
```
GET /api/stats?profile_id=<uuid>&period=month
GET /api/stats/streak?profile_id=<uuid>
GET /api/stats/calendar?profile_id=<uuid>&weeks=12
```

**Визуализация в Mini App:**
- График активности (календарь)
- Круговая диаграмма по оценкам (know/repeat/dont_know)
- Прогресс-бар до следующего уровня
- Счетчик streak
- Топ-5 самых изученных колод

---

Документ backend-flashcards.md теперь полностью заполнен и описывает всю систему карточек для изучения языков.
