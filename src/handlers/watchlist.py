import re
from html import escape
from urllib.parse import parse_qs, urlparse

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from src.app_context import AppContext
from src.keyboards.watchlist import (
    get_add_target_keyboard,
    get_dashboard_keyboard,
    get_target_manage_keyboard,
    get_targets_list_keyboard,
)
from src.services.monitoring import MonitoringService
from src.services.target_storage import TargetStorage
from src.states.target import TargetStates


def _dashboard_text(context: AppContext) -> str:
    total = len(context.targets)
    active = len(context.get_active_targets())
    location = escape(context.search_config.location_label)
    return (
        "🧭 <b>Панель управления парсером</b>\n\n"
        f"🌍 Локация: <b>{location}</b>\n"
        f"📡 Категорий: <b>{total}</b> (активных: <b>{active}</b>)\n\n"
        "Выбери действие ниже."
    )


def _targets_text(context: AppContext) -> str:
    if not context.targets:
        return "📭 Категории пока не добавлены.\n\nНажми <b>➕ Добавить</b>."

    lines = ["📡 <b>Категории в мониторинге:</b>", ""]
    for target in context.targets.values():
        status = "🟢" if target.enabled else "⏸"
        lines.append(f"{status} <b>{escape(target.name)}</b> (cat={target.category_id})")
    return "\n".join(lines)


def _parse_target_source(text: str) -> tuple[int, dict[str, str], str]:
    payload = text.strip()
    if not payload:
        raise ValueError("Пустой ввод.")

    if payload.isdigit():
        category_id = int(payload)
        if category_id <= 0:
            raise ValueError("ID категории должен быть больше 0.")
        return category_id, {}, f"Категория {category_id}"

    match = re.fullmatch(r"cat=(\d+)", payload)
    if match:
        category_id = int(match.group(1))
        if category_id <= 0:
            raise ValueError("ID категории должен быть больше 0.")
        return category_id, {}, f"Категория {category_id}"

    if payload.startswith("http://") or payload.startswith("https://"):
        parsed = urlparse(payload)
        query = parse_qs(parsed.query)

        cat_raw = query.get("cat", [None])[0]
        if not cat_raw or not str(cat_raw).isdigit():
            raise ValueError("В ссылке не найден параметр cat=...")

        category_id = int(str(cat_raw))
        if category_id <= 0:
            raise ValueError("ID категории должен быть больше 0.")
        extra_params: dict[str, str] = {}
        for key, values in query.items():
            if key in {"cat", "rgn", "ar"}:
                continue
            if not values:
                continue
            value = values[0].strip()
            if value:
                extra_params[key] = value

        if "query" in extra_params:
            auto_name = f"{extra_params['query']} (cat {category_id})"
        else:
            auto_name = f"Категория {category_id}"

        return category_id, extra_params, auto_name

    raise ValueError("Нужен ID категории (например 17010) или полная ссылка Kufar.")


def build_watchlist_router(
    context: AppContext,
    monitoring_service: MonitoringService,
    target_storage: TargetStorage,
) -> Router:
    router = Router(name="watchlist")

    @router.message(Command("menu"))
    async def cmd_menu(message: Message) -> None:
        await message.answer(_dashboard_text(context), reply_markup=get_dashboard_keyboard(), parse_mode="HTML")

    @router.message(Command("targets"))
    async def cmd_targets(message: Message) -> None:
        await message.answer(
            _targets_text(context),
            reply_markup=get_targets_list_keyboard(list(context.targets.values())),
            parse_mode="HTML",
        )

    @router.callback_query(F.data == "menu_open")
    async def menu_open(callback: CallbackQuery) -> None:
        await callback.message.edit_text(
            _dashboard_text(context),
            reply_markup=get_dashboard_keyboard(),
            parse_mode="HTML",
        )
        await callback.answer()

    @router.callback_query(F.data == "menu_targets")
    async def menu_targets(callback: CallbackQuery) -> None:
        await callback.message.edit_text(
            _targets_text(context),
            reply_markup=get_targets_list_keyboard(list(context.targets.values())),
            parse_mode="HTML",
        )
        await callback.answer()

    @router.callback_query(F.data == "menu_add_target")
    async def menu_add_target(callback: CallbackQuery, state: FSMContext) -> None:
        await state.set_state(TargetStates.waiting_for_source)
        await callback.message.answer(
            (
                "➕ <b>Добавление категории</b>\n\n"
                "Отправь:\n"
                "1) ID категории (пример: <code>17010</code>)\n"
                "или\n"
                "2) Полную ссылку поиска Kufar (оттуда возьмутся фильтры).\n\n"
                "📌 Как быстро взять ID категории:\n"
                "Открой нужную категорию на Kufar -> нажми F12 -> Network -> в фильтр введи <code>cat</code> -> "
                "открой любой запрос и в <b>Request URL</b> возьми число после <code>?cat=</code>."
            ),
            reply_markup=get_add_target_keyboard(),
            parse_mode="HTML",
        )
        await callback.answer()

    @router.callback_query(F.data == "target_add_cancel")
    async def target_add_cancel(callback: CallbackQuery, state: FSMContext) -> None:
        await state.clear()
        await callback.message.edit_text(
            "Операция добавления отменена.",
            reply_markup=get_dashboard_keyboard(),
        )
        await callback.answer()

    @router.message(StateFilter(TargetStates.waiting_for_source))
    async def target_source_input(message: Message, state: FSMContext) -> None:
        try:
            category_id, extra_params, auto_name = _parse_target_source(message.text or "")
        except ValueError as error:
            await message.answer(
                f"❌ {error}\n\nПопробуй ещё раз или нажми /menu.",
                reply_markup=get_add_target_keyboard(),
            )
            return

        duplicate = next(
            (
                target
                for target in context.targets.values()
                if target.category_id == category_id and target.extra_params == extra_params
            ),
            None,
        )
        if duplicate:
            await state.clear()
            await message.answer(
                (
                    f"⚠️ Такой трек уже есть: <b>{escape(duplicate.name)}</b>\n"
                    f"cat={duplicate.category_id}"
                ),
                parse_mode="HTML",
            )
            return

        await state.update_data(
            category_id=category_id,
            extra_params=extra_params,
            auto_name=auto_name,
        )
        await state.set_state(TargetStates.waiting_for_name)
        await message.answer(
            (
                f"Найдено: <code>cat={category_id}</code>\n"
                f"Автоназвание: <b>{escape(auto_name)}</b>\n\n"
                "Отправь имя для этой категории.\n"
                "Если оставить автоназвание, отправь <code>-</code>."
            ),
            parse_mode="HTML",
            reply_markup=get_add_target_keyboard(),
        )

    @router.message(StateFilter(TargetStates.waiting_for_name))
    async def target_name_input(message: Message, state: FSMContext) -> None:
        data = await state.get_data()
        category_id = data.get("category_id")
        extra_params = data.get("extra_params", {})
        auto_name = data.get("auto_name", "Новая категория")
        if not category_id:
            await state.clear()
            await message.answer("Сессия добавления устарела. Нажми /menu и попробуй снова.")
            return

        raw_name = (message.text or "").strip()
        name = auto_name if raw_name in {"", "-"} else raw_name[:60]

        target = context.add_target(name=name, category_id=int(category_id), extra_params=extra_params)
        target_storage.save(context)
        await monitoring_service.update_target_baseline(target)
        await state.clear()

        await message.answer(
            (
                f"✅ Категория добавлена: <b>{escape(target.name)}</b>\n"
                f"<code>{escape(target.debug_label)}</code>"
            ),
            parse_mode="HTML",
        )
        await message.answer(
            _dashboard_text(context),
            reply_markup=get_dashboard_keyboard(),
            parse_mode="HTML",
        )

    @router.callback_query(F.data.startswith("target_open_"))
    async def target_open(callback: CallbackQuery) -> None:
        target_id = int(callback.data.split("_")[2])
        target = context.targets.get(target_id)
        if not target:
            await callback.answer("Категория не найдена", show_alert=True)
            return

        status = "Активна" if target.enabled else "На паузе"
        text = (
            f"🎯 <b>{escape(target.name)}</b>\n\n"
            f"Статус: <b>{status}</b>\n"
            f"Параметры: <code>{escape(target.debug_label)}</code>\n"
            f"Локация: <b>{escape(context.search_config.location_label)}</b>"
        )
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=get_target_manage_keyboard(target))
        await callback.answer()

    @router.callback_query(F.data.startswith("target_toggle_"))
    async def target_toggle(callback: CallbackQuery) -> None:
        target_id = int(callback.data.split("_")[2])
        target = context.toggle_target(target_id)
        if not target:
            await callback.answer("Категория не найдена", show_alert=True)
            return

        target_storage.save(context)
        if target.enabled:
            await monitoring_service.update_target_baseline(target)

        status = "включена" if target.enabled else "поставлена на паузу"
        await callback.answer(f"Категория {status}")

        text = (
            f"🎯 <b>{escape(target.name)}</b>\n\n"
            f"Статус: <b>{'Активна' if target.enabled else 'На паузе'}</b>\n"
            f"Параметры: <code>{escape(target.debug_label)}</code>\n"
            f"Локация: <b>{escape(context.search_config.location_label)}</b>"
        )
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=get_target_manage_keyboard(target))

    @router.callback_query(F.data.startswith("target_remove_"))
    async def target_remove(callback: CallbackQuery) -> None:
        target_id = int(callback.data.split("_")[2])
        target = context.targets.get(target_id)
        if not target:
            await callback.answer("Категория уже удалена", show_alert=True)
            return

        context.remove_target(target_id)
        target_storage.save(context)
        to_delete = [
            key
            for key in context.ad_photos_cache
            if isinstance(key, str) and key.startswith(f"track_{target_id}_")
        ]
        for key in to_delete:
            context.ad_photos_cache.pop(key, None)

        for user_id, session in list(context.browsing_sessions.items()):
            if session.get("target_id") == target_id:
                context.browsing_sessions.pop(user_id, None)

        await callback.message.edit_text(
            f"🗑 Категория удалена: <b>{escape(target.name)}</b>",
            parse_mode="HTML",
            reply_markup=get_targets_list_keyboard(list(context.targets.values())),
        )
        await callback.answer()

    @router.callback_query(F.data.startswith("target_baseline_"))
    async def target_baseline(callback: CallbackQuery) -> None:
        target_id = int(callback.data.split("_")[2])
        target = context.targets.get(target_id)
        if not target:
            await callback.answer("Категория не найдена", show_alert=True)
            return

        count = await monitoring_service.update_target_baseline(target)
        await callback.answer(f"Baseline обновлен ({count})")
        await callback.message.edit_text(
            (
                f"🎯 <b>{escape(target.name)}</b>\n\n"
                f"Статус: <b>{'Активна' if target.enabled else 'На паузе'}</b>\n"
                f"Параметры: <code>{escape(target.debug_label)}</code>\n"
                f"Локация: <b>{escape(context.search_config.location_label)}</b>\n\n"
                f"Baseline: {count} объявлений."
            ),
            parse_mode="HTML",
            reply_markup=get_target_manage_keyboard(target),
        )

    @router.callback_query(F.data == "menu_rebaseline")
    async def menu_rebaseline(callback: CallbackQuery) -> None:
        total = await monitoring_service.update_all_baselines()
        await callback.answer(f"Готово: {total} объявлений в baseline", show_alert=True)
        await callback.message.edit_text(
            _dashboard_text(context),
            reply_markup=get_dashboard_keyboard(),
            parse_mode="HTML",
        )

    return router
