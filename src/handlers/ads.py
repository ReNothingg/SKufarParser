from aiogram import Bot, F, Router
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InputMediaPhoto, Message
from html import escape

from src.app_context import AppContext
from src.models.search_target import SearchTarget
from src.keyboards.ads import get_target_picker_keyboard, get_view_keyboard
from src.keyboards.watchlist import get_dashboard_keyboard


def _get_enabled_targets(context: AppContext) -> list[SearchTarget]:
    return [target for target in context.targets.values() if target.enabled]


def _build_start_text(context: AppContext) -> str:
    active_targets = context.get_active_targets()
    total_targets = len(context.targets)
    paused_targets = total_targets - len(active_targets)
    location = escape(context.search_config.location_label)

    if active_targets:
        preview_lines = [f"• {escape(target.name)}" for target in active_targets[:5]]
        if len(active_targets) > 5:
            preview_lines.append(f"• ...и еще {len(active_targets) - 5}")
        active_preview = "\n".join(preview_lines)
    else:
        active_preview = "• Нет активных категорий"

    return (
        "<b>SKufar Parser Bot</b>\n"
        "Мониторит новые объявления и присылает их в Telegram.\n\n"
        "<b>Текущее состояние:</b>\n"
        f"🌍 Локация: <b>{location}</b>\n"
        f"📡 Категорий: <b>{total_targets}</b> (активных: <b>{len(active_targets)}</b>, на паузе: <b>{paused_targets}</b>)\n\n"
        "<b>Активные категории:</b>\n"
        f"{active_preview}\n\n"
        "<b>Быстрый старт:</b>\n"
        "1. /menu - добавить или настроить категории.\n"
        "2. /set_location - выбрать регион/город.\n"
        "3. /all - открыть ручной просмотр объявлений."
    )


async def _start_all_flow(
    bot: Bot,
    context: AppContext,
    chat_id: int,
    user_id: int,
    message_to_edit: Message | None = None,
) -> None:
    enabled_targets = _get_enabled_targets(context)
    if not enabled_targets:
        text = (
            "📭 Нет активных категорий для просмотра.\n\n"
            "Добавь хотя бы одну в /menu."
        )
        if message_to_edit:
            await message_to_edit.edit_text(text)
        else:
            await bot.send_message(chat_id, text)
        return

    if len(enabled_targets) == 1:
        target = enabled_targets[0]
        await _open_target_ads(
            bot=bot,
            context=context,
            chat_id=chat_id,
            user_id=user_id,
            target=target,
            message_to_edit=message_to_edit,
        )
        return

    picker_text = "Выбери категорию для просмотра объявлений:"
    keyboard = get_target_picker_keyboard(enabled_targets)
    if message_to_edit:
        await message_to_edit.edit_text(picker_text, reply_markup=keyboard)
    else:
        await bot.send_message(chat_id, picker_text, reply_markup=keyboard)


async def _open_target_ads(
    bot: Bot,
    context: AppContext,
    chat_id: int,
    user_id: int,
    target: SearchTarget,
    message_to_edit: Message | None = None,
) -> None:
    if message_to_edit:
        await message_to_edit.edit_text(f"⏳ Загружаю категорию: {escape(target.name)}...")

    ads = await context.parser.fetch_search_results(context.search_config, target)
    if not ads:
        text = f"❌ В категории <b>{escape(target.name)}</b> объявлений нет."
        if message_to_edit:
            await message_to_edit.edit_text(text, parse_mode=ParseMode.HTML)
        else:
            await bot.send_message(chat_id, text, parse_mode=ParseMode.HTML)
        return

    context.browsing_sessions[user_id] = {"ads": ads, "index": 0, "target_id": target.target_id}
    await _update_ad_view(
        bot=bot,
        context=context,
        chat_id=chat_id,
        user_id=user_id,
        message_to_edit=message_to_edit,
    )


async def _update_ad_view(
    bot: Bot,
    context: AppContext,
    chat_id: int,
    user_id: int,
    message_to_edit: Message | None = None,
    message_id: int | None = None,
) -> None:
    session = context.browsing_sessions.get(user_id)
    if not session:
        return

    ads = session["ads"]
    index = session["index"]
    current_ad = ads[index]
    link = current_ad.get("ad_link", "https://www.kufar.by/")
    target_id = session.get("target_id")
    target = context.targets.get(target_id)

    details = await context.parser.fetch_ad_details(link)
    ad_data = details if details else current_ad

    text = context.parser.format_caption(ad_data, index, len(ads))
    if target:
        text = f"🏷 <b>{escape(target.name)}</b>\n{text}"
    photos = context.parser.get_all_photos(ad_data)
    context.ad_photos_cache[f"view_{user_id}"] = photos

    keyboard = get_view_keyboard(link, index, len(ads), len(photos) > 1)
    media = InputMediaPhoto(media=photos[0], caption=text, parse_mode=ParseMode.HTML)

    try:
        if message_to_edit:
            await message_to_edit.delete()
            await bot.send_photo(
                chat_id,
                photo=photos[0],
                caption=text,
                reply_markup=keyboard,
                parse_mode=ParseMode.HTML,
            )
        elif message_id:
            await bot.edit_message_media(
                chat_id=chat_id,
                message_id=message_id,
                media=media,
                reply_markup=keyboard,
            )
    except Exception:
        await bot.send_photo(
            chat_id,
            photo=photos[0],
            caption=text,
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML,
        )


def build_ads_router(context: AppContext, bot: Bot) -> Router:
    router = Router(name="ads")

    @router.message(Command("start"))
    async def cmd_start(message: Message) -> None:
        await message.answer(
            _build_start_text(context),
            parse_mode=ParseMode.HTML,
            reply_markup=get_dashboard_keyboard(),
        )

    @router.message(Command("all"))
    async def cmd_view_all(message: Message) -> None:
        wait_message = await message.answer("⏳ Проверяю категории...")
        await _start_all_flow(bot, context, message.chat.id, message.from_user.id, message_to_edit=wait_message)

    @router.callback_query(F.data == "menu_all")
    async def menu_all(callback: CallbackQuery) -> None:
        await _start_all_flow(bot, context, callback.message.chat.id, callback.from_user.id)
        await callback.answer()

    @router.callback_query(F.data.startswith("allpick_"))
    async def allpick_target(callback: CallbackQuery) -> None:
        if callback.data == "allpick_cancel":
            await callback.message.delete()
            await callback.answer()
            return

        target_id = int(callback.data.split("_")[1])
        target = context.targets.get(target_id)
        if not target or not target.enabled:
            await callback.answer("Категория недоступна", show_alert=True)
            return

        await _open_target_ads(
            bot=bot,
            context=context,
            chat_id=callback.message.chat.id,
            user_id=callback.from_user.id,
            target=target,
            message_to_edit=callback.message,
        )
        await callback.answer()

    @router.callback_query(F.data.startswith("nav_"))
    async def process_navigation(callback: CallbackQuery) -> None:
        user_id = callback.from_user.id
        action = callback.data.split("_")[1]

        if user_id not in context.browsing_sessions:
            await callback.answer("Сессия истекла")
            return

        session = context.browsing_sessions[user_id]
        total = len(session["ads"])

        if action == "next":
            session["index"] = (session["index"] + 1) % total
            await _update_ad_view(bot, context, callback.message.chat.id, user_id, message_id=callback.message.message_id)
            await callback.answer()
            return

        if action == "prev":
            session["index"] = (session["index"] - 1 + total) % total
            await _update_ad_view(bot, context, callback.message.chat.id, user_id, message_id=callback.message.message_id)
            await callback.answer()
            return

        if action == "photos":
            photos = context.ad_photos_cache.get(f"view_{user_id}", [])
            if photos:
                media = [InputMediaPhoto(media=url) for url in photos[:10]]
                await bot.send_media_group(callback.message.chat.id, media=media)
            await callback.answer()
            return

        if action == "close":
            context.browsing_sessions.pop(user_id, None)
            context.ad_photos_cache.pop(f"view_{user_id}", None)
            await callback.message.delete()
            await callback.answer()
            return

        await callback.answer()

    @router.callback_query(F.data.startswith("show_pics_"))
    async def process_show_photos(callback: CallbackQuery) -> None:
        cache_key = callback.data.replace("show_pics_", "", 1)
        photos = context.ad_photos_cache.get(cache_key)
        if not photos:
            await callback.answer("Фото устарели", show_alert=True)
            return

        await callback.answer("Отправляю...")
        media = [InputMediaPhoto(media=url) for url in photos[:10]]
        await bot.send_media_group(callback.message.chat.id, media=media)

    return router
