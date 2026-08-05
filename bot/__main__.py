import asyncio
import logging

from aiogram import Bot, Dispatcher

from core.config import get_settings
from bot.handlers import payment, start
from bot.i18n import i18n_middleware
from bot.middlewares import DbSessionMiddleware

logging.basicConfig(level=logging.INFO)


async def main():
    settings = get_settings()
    bot = Bot(token=settings.bot_token)
    dp = Dispatcher()

    dp.update.middleware(i18n_middleware)
    dp.update.middleware(DbSessionMiddleware())

    # payment first: its F.successful_payment / pre_checkout filters are narrow, and
    # start.py ends with a catch-all F.photo handler.
    dp.include_router(payment.router)
    dp.include_router(start.router)

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
