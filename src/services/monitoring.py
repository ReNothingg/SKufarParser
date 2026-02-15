import asyncio
import logging

from aiogram import Bot
from aiogram.enums import ParseMode

from src.app_context import AppContext
from src.config import AppConfig
from src.keyboards.ads import get_monitor_keyboard


class MonitoringService:
    def __init__(self, context: AppContext, bot: Bot, config: AppConfig):
        self.context = context
        self.bot = bot
        self.config = config

    async def update_seen_ads_baseline(self) -> None:
        self.context.seen_ads.clear()
        ads = await self.context.parser.fetch_search_results(self.context.search_config)
        for ad in ads:
            ad_id = ad.get("ad_id")
            if ad_id:
                self.context.seen_ads.add(ad_id)
        logging.info("База baseline обновлена: %s объявлений.", len(ads))

    async def background_monitoring(self) -> None:
        logging.info("Мониторинг запущен.")
        while True:
            await asyncio.sleep(self.config.check_interval)
            try:
                new_ads = await self.context.parser.fetch_search_results(self.context.search_config)
                for ad in reversed(new_ads):
                    ad_id = ad.get("ad_id")
                    if not ad_id or ad_id in self.context.seen_ads:
                        continue

                    self.context.seen_ads.add(ad_id)

                    link = ad.get("ad_link")
                    details = await self.context.parser.fetch_ad_details(link) if link else None
                    payload = details if details else ad

                    caption = self.context.parser.format_caption(payload)
                    photos = self.context.parser.get_all_photos(payload)

                    if len(photos) > 1:
                        self.context.ad_photos_cache[ad_id] = photos

                    keyboard = get_monitor_keyboard(link or "https://www.kufar.by/", ad_id, len(photos) > 1)

                    try:
                        await self.bot.send_photo(
                            self.config.user_id,
                            photo=photos[0],
                            caption=caption,
                            reply_markup=keyboard,
                            parse_mode=ParseMode.HTML,
                        )
                        logging.info("Новое объявление: %s", ad_id)
                    except Exception as error:
                        logging.error("Не удалось отправить объявление %s: %s", ad_id, error)

                    await asyncio.sleep(1)
            except Exception as error:
                logging.error("Ошибка мониторинга: %s", error)

