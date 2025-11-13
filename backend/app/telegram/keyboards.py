"""Inline keyboards for Telegram bot."""

from __future__ import annotations

from typing import Sequence
from urllib.parse import urlencode

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

# Callback data prefixes for different action types
CALLBACK_ADD_CARD = "add_card"
CALLBACK_REMOVE_CARD = "remove_card"
CALLBACK_PAGE = "page"
CALLBACK_CANCEL = "cancel"


def create_add_to_cards_keyboard(word: str, translation: str) -> InlineKeyboardMarkup:
    """
    Create keyboard with "Add to cards" button.

    Args:
        word: Word to add
        translation: Translation of the word

    Returns:
        Inline keyboard
    """
    # Encode word and translation for callback data
    # Format: add_card:word:translation
    callback_data = f"{CALLBACK_ADD_CARD}:{word}:{translation}"

    # Telegram limits callback_data to 64 bytes
    if len(callback_data.encode("utf-8")) > 64:
        # If too long, use short format
        # Callback handler will need to extract data from message
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
    Create keyboard with actions for a card.

    Args:
        card_id: Card ID
        show_mini_app: Whether to show "Open Mini App" button

    Returns:
        Inline keyboard
    """
    keyboard: list[list[InlineKeyboardButton]] = []

    # Delete card button
    keyboard.append(
        [InlineKeyboardButton("🗑 Удалить", callback_data=f"{CALLBACK_REMOVE_CARD}:{card_id}")]
    )

    # Open Mini App button (optional)
    if show_mini_app:
        keyboard.append([create_mini_app_button()])

    return InlineKeyboardMarkup(keyboard)


def create_mini_app_button(
    text: str = "🚀 Открыть Mini App",
    path: str = "",
    params: dict[str, str] | None = None,
) -> InlineKeyboardButton:
    """
    Create button for opening Mini App.

    Args:
        text: Button text
        path: Path inside Mini App (e.g., "/practice/cards")
        params: Query parameters to pass to Mini App

    Returns:
        Inline button
    """
    # TODO: get APP_URL from settings
    # Using placeholder for now
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
    """Calculate page range for display."""
    half_window = items_per_row // 2
    start_page = max(1, current_page - half_window)
    end_page = min(total_pages, start_page + items_per_row - 1)

    # Adjust start_page if end_page hits the maximum
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
    """Create row with page navigation."""
    nav_row: list[InlineKeyboardButton] = []

    # "< Prev" button
    if current_page > 1:
        nav_row.append(
            InlineKeyboardButton(
                "⬅️ Пред",
                callback_data=f"{callback_prefix}:{current_page - 1}",
            )
        )

    # Page numbers
    for page in range(start_page, end_page + 1):
        text = f"· {page} ·" if page == current_page else str(page)
        nav_row.append(
            InlineKeyboardButton(
                text,
                callback_data=f"{callback_prefix}:{page}",
            )
        )

    # "Next >" button
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
    """Create additional row with "To start" and "To end" buttons."""
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
    Create keyboard for pagination.

    Args:
        current_page: Current page (starting from 1)
        total_pages: Total number of pages
        callback_prefix: Prefix for callback_data
        items_per_row: Number of page number buttons in a row

    Returns:
        Inline keyboard with navigation

    Example:
        For current_page=3, total_pages=10:
        [< Prev] [1] [2] [3] [4] [5] [Next >]
    """
    keyboard: list[list[InlineKeyboardButton]] = []

    # If only one page, don't show pagination
    if total_pages <= 1:
        return InlineKeyboardMarkup(keyboard)

    # Determine page range for display
    start_page, end_page = _calculate_page_range(current_page, total_pages, items_per_row)

    # Navigation row
    nav_row = _create_navigation_row(
        current_page, total_pages, start_page, end_page, callback_prefix
    )
    keyboard.append(nav_row)

    # Additional row with "To start" and "To end" buttons (if needed)
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
    Create keyboard with list of items and pagination.

    Args:
        items: List of tuples (button_text, callback_data)
        current_page: Current page (starting from 1)
        items_per_page: Number of items per page
        callback_prefix: Prefix for pagination callback_data

    Returns:
        Inline keyboard

    Example:
        >>> items = [("Item 1", "item:1"), ("Item 2", "item:2"), ...]
        >>> keyboard = create_list_with_pagination(items, current_page=1)
    """
    keyboard: list[list[InlineKeyboardButton]] = []

    # Calculate item range for current page
    total_items = len(items)
    total_pages = (total_items + items_per_page - 1) // items_per_page
    start_idx = (current_page - 1) * items_per_page
    end_idx = min(start_idx + items_per_page, total_items)

    # Add item buttons
    for text, callback_data in items[start_idx:end_idx]:
        keyboard.append([InlineKeyboardButton(text, callback_data=callback_data)])

    # Add pagination if needed
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
    Create confirmation action keyboard.

    Args:
        confirm_data: callback_data for confirmation button
        cancel_data: callback_data for cancel button

    Returns:
        Inline keyboard
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
    Create empty keyboard (for removing buttons).

    Returns:
        Empty inline keyboard
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
