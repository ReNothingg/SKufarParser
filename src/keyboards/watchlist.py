from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from src.models.search_target import SearchTarget


def get_dashboard_keyboard() -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(text="📡 Категории", callback_data="menu_targets"),
            InlineKeyboardButton(text="➕ Добавить", callback_data="menu_add_target"),
        ],
        [
            InlineKeyboardButton(text="🌍 Локация", callback_data="menu_set_location"),
            InlineKeyboardButton(text="📂 Листать", callback_data="menu_all"),
        ],
        [InlineKeyboardButton(text="🔄 Rebaseline", callback_data="menu_rebaseline")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def get_targets_list_keyboard(targets: list[SearchTarget]) -> InlineKeyboardMarkup:
    rows = []
    for target in targets:
        rows.append([InlineKeyboardButton(text=target.short_label, callback_data=f"target_open_{target.target_id}")])
    rows.append(
        [
            InlineKeyboardButton(text="➕ Добавить", callback_data="menu_add_target"),
            InlineKeyboardButton(text="⬅️ В меню", callback_data="menu_open"),
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def get_target_manage_keyboard(target: SearchTarget) -> InlineKeyboardMarkup:
    toggle_label = "⏸ Пауза" if target.enabled else "▶️ Включить"
    rows = [
        [
            InlineKeyboardButton(text=toggle_label, callback_data=f"target_toggle_{target.target_id}"),
            InlineKeyboardButton(text="🗑 Удалить", callback_data=f"target_remove_{target.target_id}"),
        ],
        [InlineKeyboardButton(text="🔄 Rebaseline", callback_data=f"target_baseline_{target.target_id}")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="menu_targets")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def get_add_target_keyboard() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text="❌ Отмена", callback_data="target_add_cancel")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)

