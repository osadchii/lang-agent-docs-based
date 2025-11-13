"""Inline-клавиатуры для Telegram бота."""

from __future__ import annotations

from typing import Sequence
from urllib.parse import urlencode

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

# Callback data prefixes для разных типов действий
CALLBACK_ADD_CARD = "add_card"
CALLBACK_REMOVE_CARD = "remove_card"
CALLBACK_PAGE = "page"
CALLBACK_CANCEL = "cancel"


def create_add_to_cards_keyboard(word: str, translation: str) -> InlineKeyboardMarkup:
    """
    Создать клавиатуру с кнопкой "Добавить в карточки".

    Args:
        word: Слово для добавления
        translation: Перевод слова

    Returns:
        Inline-клавиатура
    """
    # Encode word and translation for callback data
    # Формат: add_card:word:translation
    callback_data = f"{CALLBACK_ADD_CARD}:{word}:{translation}"

    # Telegram ограничивает callback_data до 64 байт
    if len(callback_data.encode("utf-8")) > 64:
        # Если слишком длинно, используем короткий формат
        # В callback handler потребуется получить данные из сообщения
        callback_data = f"{CALLBACK_ADD_CARD}:from_message"

    keyboard = [
        [InlineKeyboardButton("📝 Добавить в карточки", callback_data=callback_data)],
    ]

    return InlineKeyboardMarkup(keyboard)


def create_card_actions_keyboard(
    card_id: str,
    show_mini_app: bool = True,
) -> InlineKeyboardMarkup:
    """
    Создать клавиатуру с действиями для карточки.

    Args:
        card_id: ID карточки
        show_mini_app: Показывать ли кнопку "Открыть Mini App"

    Returns:
        Inline-клавиатура
    """
    keyboard: list[list[InlineKeyboardButton]] = []

    # Кнопка удаления карточки
    keyboard.append(
        [InlineKeyboardButton("🗑 Удалить", callback_data=f"{CALLBACK_REMOVE_CARD}:{card_id}")]
    )

    # Кнопка открытия Mini App (опционально)
    if show_mini_app:
        keyboard.append([create_mini_app_button()])

    return InlineKeyboardMarkup(keyboard)


def create_mini_app_button(
    text: str = "🚀 Открыть Mini App",
    path: str = "",
    params: dict[str, str] | None = None,
) -> InlineKeyboardButton:
    """
    Создать кнопку для открытия Mini App.

    Args:
        text: Текст кнопки
        path: Путь внутри Mini App (например, "/practice/cards")
        params: Query параметры для передачи в Mini App

    Returns:
        Inline-кнопка
    """
    # TODO: получить APP_URL из настроек
    # Пока используем placeholder
    base_url = "https://your-mini-app.com"

    url = base_url + path
    if params:
        url += "?" + urlencode(params)

    return InlineKeyboardButton(text, web_app=WebAppInfo(url=url))


def _calculate_page_range(
    current_page: int,
    total_pages: int,
    items_per_row: int,
) -> tuple[int, int]:
    """Вычислить диапазон страниц для отображения."""
    half_window = items_per_row // 2
    start_page = max(1, current_page - half_window)
    end_page = min(total_pages, start_page + items_per_row - 1)

    # Корректируем start_page если end_page упирается в максимум
    if end_page == total_pages and end_page - start_page + 1 < items_per_row:
        start_page = max(1, end_page - items_per_row + 1)

    return start_page, end_page


def _create_navigation_row(
    current_page: int,
    total_pages: int,
    start_page: int,
    end_page: int,
    callback_prefix: str,
) -> list[InlineKeyboardButton]:
    """Создать ряд с навигацией по страницам."""
    nav_row: list[InlineKeyboardButton] = []

    # Кнопка "< Пред"
    if current_page > 1:
        nav_row.append(
            InlineKeyboardButton(
                "⬅️ Пред",
                callback_data=f"{callback_prefix}:{current_page - 1}",
            )
        )

    # Номера страниц
    for page in range(start_page, end_page + 1):
        text = f"· {page} ·" if page == current_page else str(page)
        nav_row.append(
            InlineKeyboardButton(
                text,
                callback_data=f"{callback_prefix}:{page}",
            )
        )

    # Кнопка "След >"
    if current_page < total_pages:
        nav_row.append(
            InlineKeyboardButton(
                "След ➡️",
                callback_data=f"{callback_prefix}:{current_page + 1}",
            )
        )

    return nav_row


def _create_extra_navigation_row(
    current_page: int,
    total_pages: int,
    items_per_row: int,
    callback_prefix: str,
) -> list[InlineKeyboardButton]:
    """Создать дополнительный ряд с кнопками "В начало" и "В конец"."""
    extra_row: list[InlineKeyboardButton] = []
    half_window = items_per_row // 2

    if current_page > half_window + 1:
        extra_row.append(
            InlineKeyboardButton(
                "⏮ В начало",
                callback_data=f"{callback_prefix}:1",
            )
        )

    if current_page < total_pages - half_window:
        extra_row.append(
            InlineKeyboardButton(
                "В конец ⏭",
                callback_data=f"{callback_prefix}:{total_pages}",
            )
        )

    return extra_row


def create_pagination_keyboard(
    current_page: int,
    total_pages: int,
    callback_prefix: str = CALLBACK_PAGE,
    items_per_row: int = 5,
) -> InlineKeyboardMarkup:
    """
    Создать клавиатуру для пагинации.

    Args:
        current_page: Текущая страница (начиная с 1)
        total_pages: Общее количество страниц
        callback_prefix: Префикс для callback_data
        items_per_row: Количество кнопок-номеров в ряду

    Returns:
        Inline-клавиатура с навигацией

    Example:
        Для current_page=3, total_pages=10:
        [< Пред] [1] [2] [3] [4] [5] [След >]
    """
    keyboard: list[list[InlineKeyboardButton]] = []

    # Если всего одна страница, не показываем пагинацию
    if total_pages <= 1:
        return InlineKeyboardMarkup(keyboard)

    # Определяем диапазон страниц для отображения
    start_page, end_page = _calculate_page_range(current_page, total_pages, items_per_row)

    # Ряд с навигацией
    nav_row = _create_navigation_row(
        current_page, total_pages, start_page, end_page, callback_prefix
    )
    keyboard.append(nav_row)

    # Дополнительный ряд с кнопками "В начало" и "В конец" (если нужно)
    if total_pages > items_per_row:
        extra_row = _create_extra_navigation_row(
            current_page, total_pages, items_per_row, callback_prefix
        )
        if extra_row:
            keyboard.append(extra_row)

    return InlineKeyboardMarkup(keyboard)


def create_list_with_pagination(
    items: Sequence[tuple[str, str]],
    current_page: int,
    items_per_page: int = 5,
    callback_prefix: str = "select",
) -> InlineKeyboardMarkup:
    """
    Создать клавиатуру со списком элементов и пагинацией.

    Args:
        items: Список кортежей (текст_кнопки, callback_data)
        current_page: Текущая страница (начиная с 1)
        items_per_page: Количество элементов на странице
        callback_prefix: Префикс для callback_data пагинации

    Returns:
        Inline-клавиатура

    Example:
        >>> items = [("Item 1", "item:1"), ("Item 2", "item:2"), ...]
        >>> keyboard = create_list_with_pagination(items, current_page=1)
    """
    keyboard: list[list[InlineKeyboardButton]] = []

    # Вычисляем диапазон элементов для текущей страницы
    total_items = len(items)
    total_pages = (total_items + items_per_page - 1) // items_per_page
    start_idx = (current_page - 1) * items_per_page
    end_idx = min(start_idx + items_per_page, total_items)

    # Добавляем кнопки с элементами
    for text, callback_data in items[start_idx:end_idx]:
        keyboard.append([InlineKeyboardButton(text, callback_data=callback_data)])

    # Добавляем пагинацию если нужно
    if total_pages > 1:
        pagination = create_pagination_keyboard(current_page, total_pages, callback_prefix)
        for row in pagination.inline_keyboard:
            keyboard.append(list(row))

    return InlineKeyboardMarkup(keyboard)


def create_confirmation_keyboard(
    confirm_data: str,
    cancel_data: str = CALLBACK_CANCEL,
) -> InlineKeyboardMarkup:
    """
    Создать клавиатуру подтверждения действия.

    Args:
        confirm_data: callback_data для кнопки подтверждения
        cancel_data: callback_data для кнопки отмены

    Returns:
        Inline-клавиатура
    """
    keyboard = [
        [
            InlineKeyboardButton("✅ Подтвердить", callback_data=confirm_data),
            InlineKeyboardButton("❌ Отмена", callback_data=cancel_data),
        ],
    ]

    return InlineKeyboardMarkup(keyboard)


def remove_keyboard() -> InlineKeyboardMarkup:
    """
    Создать пустую клавиатуру (для удаления кнопок).

    Returns:
        Пустая inline-клавиатура
    """
    return InlineKeyboardMarkup([])


__all__ = [
    "create_add_to_cards_keyboard",
    "create_card_actions_keyboard",
    "create_mini_app_button",
    "create_pagination_keyboard",
    "create_list_with_pagination",
    "create_confirmation_keyboard",
    "remove_keyboard",
    "CALLBACK_ADD_CARD",
    "CALLBACK_REMOVE_CARD",
    "CALLBACK_PAGE",
    "CALLBACK_CANCEL",
]
