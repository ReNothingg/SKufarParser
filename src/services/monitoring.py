import asyncio
import logging
from html import escape

from aiogram import Bot
from aiogram.enums import ParseMode

from src.app_context import AppContext
from src.config import AppConfig
from src.models.search_target import SearchTarget
from src.keyboards.ads import get_monitor_keyboard


class MonitoringService:
    def __init__(self, context: AppContext, bot: Bot, config: AppConfig):
        self.context = context
        self.bot = bot
        self.config = config

    async def update_target_baseline(self, target: SearchTarget) -> int:
        seen_set = self.context.seen_ads_by_target.setdefault(target.target_id, set())
        seen_set.clear()
        ads = await self.context.parser.fetch_search_results(self.context.search_config, target)
        for ad in ads:
            ad_id = ad.get("ad_id")
            if ad_id:
                seen_set.add(ad_id)
        logging.info("Baseline обновлён для '%s': %s объявлений.", target.name, len(ads))
        return len(ads)

    async def update_all_baselines(self) -> int:
        total = 0
        for target in self.context.targets.values():
            if not target.enabled:
                continue
            total += await self.update_target_baseline(target)
        return total

    async def background_monitoring(self) -> None:
        logging.info("Мониторинг запущен.")
        while True:
            await asyncio.sleep(self.config.check_interval)
            try:
                active_targets = self.context.get_active_targets()
                if not active_targets:
                    continue

                for target in active_targets:
                    new_ads = await self.context.parser.fetch_search_results(self.context.search_config, target)
                    seen_set = self.context.seen_ads_by_target.setdefault(target.target_id, set())
                    for ad in reversed(new_ads):
                        ad_id = ad.get("ad_id")
                        if not ad_id or ad_id in seen_set:
                            continue

                        seen_set.add(ad_id)

                        link = ad.get("ad_link")
                        details = await self.context.parser.fetch_ad_details(link) if link else None
                        payload = details if details else ad

                        caption = self.context.parser.format_caption(payload)
                        caption = f"🏷 <b>{escape(target.name)}</b>\n{caption}"
                        photos = self.context.parser.get_all_photos(payload)

                        cache_key = f"track_{target.target_id}_{ad_id}"
                        if len(photos) > 1:
                            self.context.ad_photos_cache[cache_key] = photos

                        keyboard = get_monitor_keyboard(
                            link or "https://www.kufar.by/",
                            cache_key,
                            len(photos) > 1,
                        )

                        try:
                            await self.bot.send_photo(
                                self.config.user_id,
                                photo=photos[0],
                                caption=caption,
                                reply_markup=keyboard,
                                parse_mode=ParseMode.HTML,
                            )
                            logging.info("Новое объявление %s [%s]", ad_id, target.name)
                        except Exception as error:
                            logging.error("Не удалось отправить объявление %s: %s", ad_id, error)

                        await asyncio.sleep(1)
            except Exception as error:
                logging.error("Ошибка мониторинга: %s", error)
