from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from src.models.search_target import SearchTarget

def get_view_keyboard(url: str, current_idx: int, total: int, has_photos: bool) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(text="⬅️", callback_data="nav_prev"),
            InlineKeyboardButton(text=f"{current_idx + 1}/{total}", callback_data="nav_ignore"),
            InlineKeyboardButton(text="➡️", callback_data="nav_next"),
        ]
    ]
    if has_photos:
        rows.append([InlineKeyboardButton(text="📸 Показать все фото", callback_data="nav_photos")])
    rows.append([InlineKeyboardButton(text="🔗 На Kufar", url=url)])
    rows.append([InlineKeyboardButton(text="❌ Закрыть", callback_data="nav_close")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def get_monitor_keyboard(url: str, cache_key: str, has_multiple_photos: bool) -> InlineKeyboardMarkup:
    rows = []
    if has_multiple_photos:
        rows.append([InlineKeyboardButton(text="📸 Все фото", callback_data=f"show_pics_{cache_key}")])
    rows.append([InlineKeyboardButton(text="🔗 Открыть на Kufar", url=url)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def get_target_picker_keyboard(targets: list[SearchTarget]) -> InlineKeyboardMarkup:
    rows = []
    for target in targets:
        rows.append([InlineKeyboardButton(text=target.short_label, callback_data=f"allpick_{target.target_id}")])
    rows.append([InlineKeyboardButton(text="❌ Отмена", callback_data="allpick_cancel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
