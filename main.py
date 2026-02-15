import asyncio
import logging

from src.app import run

if __name__ == "__main__":
    try:
        asyncio.run(run())
    except (KeyboardInterrupt, SystemExit):
        pass
    except Exception:
        logging.exception("Бот остановлен из-за ошибки")
