from aiogram import F, Router
from aiogram.enums import ParseMode
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from src.app_context import AppContext
from src.services.monitoring import MonitoringService
from src.states.location import LocationStates


def _regions_keyboard(context: AppContext) -> InlineKeyboardMarkup:
    rows = []
    for region_id, region_name in sorted(context.location_manager.regions.items()):
        rows.append([InlineKeyboardButton(text=region_name, callback_data=f"setrgn_{region_id}")])

    rows.append([InlineKeyboardButton(text="🇧🇾 Вся Беларусь", callback_data="setrgn_0")])
    rows.append([InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_loc")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _areas_keyboard(context: AppContext, region_id: int, region_name: str) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text=f"📌 Весь {region_name}", callback_data="setar_0")]]
    areas = context.location_manager.areas.get(region_id, {})
    for area_id, area_name in sorted(areas.items(), key=lambda item: item[1]):
        rows.append([InlineKeyboardButton(text=area_name, callback_data=f"setar_{area_id}")])
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_regions")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def build_location_router(context: AppContext, monitoring_service: MonitoringService) -> Router:
    router = Router(name="location")

    async def _open_location_menu(message: Message, state: FSMContext) -> None:
        await message.answer("🌍 Выберите регион поиска:", reply_markup=_regions_keyboard(context))
        await state.set_state(LocationStates.waiting_for_region)

    @router.message(Command("set_location"))
    async def cmd_set_location(message: Message, state: FSMContext) -> None:
        await _open_location_menu(message, state)

    @router.callback_query(F.data == "menu_set_location")
    async def menu_set_location(callback: CallbackQuery, state: FSMContext) -> None:
        await callback.message.answer("🌍 Выберите регион поиска:", reply_markup=_regions_keyboard(context))
        await state.set_state(LocationStates.waiting_for_region)
        await callback.answer()

    @router.callback_query(StateFilter(LocationStates.waiting_for_region), F.data.startswith("setrgn_"))
    async def process_region_choice(callback: CallbackQuery, state: FSMContext) -> None:
        region_id = int(callback.data.split("_")[1])

        if region_id == 0:
            context.search_config.set_countrywide()
            await state.clear()
            await callback.message.edit_text("⏳ Обновляю настройки (Вся Беларусь)...")
            total = await monitoring_service.update_all_baselines()
            await callback.message.edit_text(
                (
                    "✅ Регион: <b>Вся Беларусь</b>.\n"
                    f"Старые объявления пропущены ({total}), жду новые..."
                ),
                parse_mode=ParseMode.HTML,
            )
            await callback.answer()
            return

        await state.update_data(rgn=region_id)
        region_name = context.location_manager.regions.get(region_id, "Неизвестно")
        keyboard = _areas_keyboard(context, region_id, region_name)
        await callback.message.edit_text(
            f"📍 Выберите город/район в <b>{region_name}</b>:",
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML,
        )
        await state.set_state(LocationStates.waiting_for_area)
        await callback.answer()

    @router.callback_query(StateFilter(LocationStates.waiting_for_area), F.data.startswith("setar_"))
    async def process_area_choice(callback: CallbackQuery, state: FSMContext) -> None:
        area_id = int(callback.data.split("_")[1])
        data = await state.get_data()
        region_id = data.get("rgn")
        if not region_id:
            await state.clear()
            await callback.answer("Сессия выбора локации устарела", show_alert=True)
            return

        region_name = context.location_manager.regions.get(region_id, "")
        context.search_config.set_region(region_id, region_name)

        if area_id == 0:
            context.search_config.set_area(None, " (Весь регион)")
        else:
            area_name = context.location_manager.areas[region_id].get(area_id, "")
            context.search_config.set_area(area_id, f", {area_name}")

        await state.clear()
        await callback.message.edit_text("⏳ Применяю настройки локации...")
        total = await monitoring_service.update_all_baselines()
        await callback.message.edit_text(
            (
                "✅ Настройки обновлены:\n"
                f"<b>{context.search_config.location_label}</b>\n\n"
                f"Старые объявления пропущены ({total}), мониторинг запущен."
            ),
            parse_mode=ParseMode.HTML,
        )
        await callback.answer()

    @router.callback_query(F.data == "back_to_regions")
    async def back_to_regions(callback: CallbackQuery, state: FSMContext) -> None:
        await callback.message.edit_text("🌍 Выберите регион поиска:", reply_markup=_regions_keyboard(context))
        await state.set_state(LocationStates.waiting_for_region)
        await callback.answer()

    @router.callback_query(F.data == "cancel_loc")
    async def cancel_loc(callback: CallbackQuery, state: FSMContext) -> None:
        await state.clear()
        await callback.message.delete()
        await callback.answer()

    return router
