import asyncio
import logging

from aiogram import Bot, Dispatcher

from bot.config import get_settings
from bot.handlers import admin, check, payment, start, voting
from bot.i18n import i18n_middleware
from bot.middlewares import DbSessionMiddleware

logging.basicConfig(level=logging.INFO)


async def main():
    settings = get_settings()
    bot = Bot(token=settings.bot_token)
    dp = Dispatcher()

    dp.update.middleware(i18n_middleware)
    dp.update.middleware(DbSessionMiddleware())

    dp.include_router(start.router)
    dp.include_router(check.router)
    dp.include_router(voting.router)
    dp.include_router(admin.router)
    dp.include_router(payment.router)

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
