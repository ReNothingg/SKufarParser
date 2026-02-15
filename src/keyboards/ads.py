from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


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
    rows.append([InlineKeyboardButton(text="🔗 На Куфар", url=url)])
    rows.append([InlineKeyboardButton(text="❌ Закрыть", callback_data="nav_close")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def get_monitor_keyboard(url: str, ad_id: int, has_multiple_photos: bool) -> InlineKeyboardMarkup:
    rows = []
    if has_multiple_photos:
        rows.append([InlineKeyboardButton(text="📸 Посмотреть все фото", callback_data=f"show_pics_{ad_id}")])
    rows.append([InlineKeyboardButton(text="🔗 Открыть на Куфар", url=url)])
    return InlineKeyboardMarkup(inline_keyboard=rows)

