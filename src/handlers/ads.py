from aiogram import Bot, F, Router
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InputMediaPhoto, Message

from src.app_context import AppContext
from src.keyboards.ads import get_view_keyboard


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

    details = await context.parser.fetch_ad_details(link)
    ad_data = details if details else current_ad

    text = context.parser.format_caption(ad_data, index, len(ads))
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
            (
                "👋 Привет! Я бот для Куфара.\n"
                f"🌍 Регион: {context.search_config.location_label}\n\n"
                "⚙️ /set_location - Изменить город/регион\n"
                "📂 /all - Просмотр объявлений списком"
            )
        )

    @router.message(Command("all"))
    async def cmd_view_all(message: Message) -> None:
        wait_message = await message.answer("⏳ Загружаю...")
        ads = await context.parser.fetch_search_results(context.search_config)
        if not ads:
            await wait_message.edit_text("❌ В этом регионе объявлений нет.")
            return

        context.browsing_sessions[message.from_user.id] = {"ads": ads, "index": 0}
        await _update_ad_view(bot, context, message.chat.id, message.from_user.id, message_to_edit=wait_message)

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
        ad_id = int(callback.data.split("_")[2])
        photos = context.ad_photos_cache.get(ad_id)
        if not photos:
            await callback.answer("Фото устарели", show_alert=True)
            return

        await callback.answer("Отправляю...")
        media = [InputMediaPhoto(media=url) for url in photos[:10]]
        await bot.send_media_group(callback.message.chat.id, media=media)

    return router

