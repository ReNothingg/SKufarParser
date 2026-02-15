import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from src.app_context import AppContext
from src.config import load_config
from src.handlers.ads import build_ads_router
from src.handlers.location import build_location_router
from src.services.kufar_parser import KufarParser
from src.services.location_manager import LocationManager
from src.services.monitoring import MonitoringService


async def run() -> None:
    logging.basicConfig(level=logging.INFO)
    config = load_config()

    location_manager = LocationManager(config.locations_file)
    parser = KufarParser(config.headers)
    context = AppContext(location_manager=location_manager, parser=parser)

    bot = Bot(token=config.bot_token)
    dp = Dispatcher(storage=MemoryStorage())
    monitoring_service = MonitoringService(context=context, bot=bot, config=config)

    dp.include_router(build_location_router(context, monitoring_service))
    dp.include_router(build_ads_router(context, bot))

    await monitoring_service.update_seen_ads_baseline()
    monitoring_task = asyncio.create_task(monitoring_service.background_monitoring())

    try:
        await dp.start_polling(bot)
    finally:
        monitoring_task.cancel()
        try:
            await monitoring_task
        except asyncio.CancelledError:
            pass

        await parser.close()
        await bot.session.close()

