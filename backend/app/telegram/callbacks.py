"""Обработчики callback-запросов от inline-кнопок."""

from __future__ import annotations

import logging
import re

from app.telegram.formatters import escape_markdown_v2, format_success_message
from app.telegram.keyboards import (
    CALLBACK_ADD_CARD,
    CALLBACK_CANCEL,
    CALLBACK_PAGE,
    CALLBACK_REMOVE_CARD,
    remove_keyboard,
)
from telegram import CallbackQuery, Message, Update
from telegram.ext import ContextTypes

logger = logging.getLogger("app.telegram.callbacks")


async def handle_callback_query(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """
    Главный обработчик всех callback-запросов.

    Маршрутизирует запросы к соответствующим обработчикам на основе callback_data.

    Args:
        update: Telegram update с callback query
        context: Контекст бота
    """
    query = update.callback_query
    if not query or not query.data:
        return

    # Обязательно отвечаем на callback query (убирает "загрузку" на кнопке)
    await query.answer()

    callback_data = query.data
    logger.info(
        "Received callback query",
        extra={
            "callback_data": callback_data,
            "user_id": update.effective_user.id if update.effective_user else None,
        },
    )

    # Маршрутизация по типу callback
    if callback_data.startswith(CALLBACK_ADD_CARD):
        await _handle_add_card(query, context)
    elif callback_data.startswith(CALLBACK_REMOVE_CARD):
        await _handle_remove_card(query, context)
    elif callback_data.startswith(CALLBACK_PAGE):
        await _handle_pagination(query, context)
    elif callback_data == CALLBACK_CANCEL:
        await _handle_cancel(query, context)
    else:
        logger.warning(
            "Unknown callback data received",
            extra={"callback_data": callback_data},
        )
        await query.answer(text="❌ Неизвестное действие", show_alert=True)


async def _handle_add_card(
    query: CallbackQuery,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """
    Обработать запрос на добавление карточки.

    Args:
        query: Callback query
        context: Контекст бота
    """
    del context  # Контекст не используется

    if not query.data or not query.message:
        return

    user = query.from_user

    # Парсим callback_data: "add_card:word:translation" или "add_card:from_message"
    parts = query.data.split(":", 2)

    if len(parts) == 3 and parts[1] != "from_message":
        word = parts[1]
        translation = parts[2]
    else:
        # Извлекаем word и translation из текста сообщения
        # Формат сообщения: "*word* — translation"
        # Проверяем что message является Message (а не MaybeInaccessibleMessage)
        if not isinstance(query.message, Message):
            await query.answer(
                text="❌ Сообщение недоступно",
                show_alert=True,
            )
            return

        text = query.message.text or query.message.caption or ""
        match = re.search(r"\*(.+?)\*\s*—\s*(.+)", text)

        if not match:
            await query.answer(
                text="❌ Не удалось извлечь данные для карточки",
                show_alert=True,
            )
            return

        word = match.group(1)
        translation = match.group(2).split("\n")[0].strip()  # Только первая строка

    # TODO: Интеграция с CardService когда он будет создан
    # Пока просто логируем и показываем заглушку
    logger.info(
        "Add card callback triggered",
        extra={
            "telegram_id": user.id,
            "word": word,
            "translation": translation,
        },
    )

    # Временная заглушка: успешное добавление
    success_text = format_success_message(
        f'Карточка "{word}" будет добавлена ' "(функционал в разработке: требуется CardService)"
    )

    await query.edit_message_text(
        text=success_text,
        parse_mode="MarkdownV2",
        reply_markup=remove_keyboard(),
    )


async def _handle_remove_card(
    query: CallbackQuery,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """
    Обработать запрос на удаление карточки.

    Args:
        query: Callback query
        context: Контекст бота
    """
    del context  # Контекст не используется

    if not query.data or not query.message:
        return

    user = query.from_user

    # Парсим callback_data: "remove_card:card_id"
    parts = query.data.split(":", 1)

    if len(parts) != 2:
        await query.answer(text="❌ Неверный формат данных", show_alert=True)
        return

    card_id = parts[1]

    # TODO: Интеграция с CardService когда он будет создан
    # Пока просто логируем и показываем заглушку
    logger.info(
        "Remove card callback triggered",
        extra={
            "telegram_id": user.id,
            "card_id": card_id,
        },
    )

    # Временная заглушка
    success_text = format_success_message(
        "Карточка будет удалена " "(функционал в разработке: требуется CardService)"
    )

    await query.edit_message_text(
        text=success_text,
        parse_mode="MarkdownV2",
        reply_markup=remove_keyboard(),
    )


async def _handle_pagination(
    query: CallbackQuery,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """
    Обработать запрос пагинации.

    Args:
        query: Callback query
        context: Контекст бота
    """
    if not query.data:
        return

    # Парсим callback_data: "page:123"
    parts = query.data.split(":", 1)

    if len(parts) != 2:
        await query.answer(text="❌ Неверный формат данных", show_alert=True)
        return

    try:
        page = int(parts[1])
    except ValueError:
        await query.answer(text="❌ Неверный номер страницы", show_alert=True)
        return

    # Сохраняем номер страницы в context.user_data для последующего использования
    if context.user_data is not None:
        context.user_data["current_page"] = page

    logger.info(
        "Pagination callback",
        extra={
            "user_id": query.from_user.id,
            "page": page,
        },
    )

    # Здесь должна быть логика обновления списка на новой странице
    # Зависит от контекста использования
    # Пока просто подтверждаем переход
    await query.answer(text=f"Страница {page}")


async def _handle_cancel(
    query: CallbackQuery,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """
    Обработать запрос отмены действия.

    Args:
        query: Callback query
        context: Контекст бота
    """
    del context  # Контекст не используется

    if not query.message:
        return

    # Удаляем клавиатуру и обновляем сообщение
    cancel_text = escape_markdown_v2("Действие отменено")

    await query.edit_message_text(
        text=cancel_text,
        parse_mode="MarkdownV2",
        reply_markup=remove_keyboard(),
    )

    await query.answer(text="❌ Отменено")


__all__ = [
    "handle_callback_query",
]
