import asyncio
import logging

from aiogram import Bot, Dispatcher

from bot.config import get_settings
from bot.handlers import admin, check, start, voting
from bot.middlewares import DbSessionMiddleware

logging.basicConfig(level=logging.INFO)


async def main():
    settings = get_settings()
    bot = Bot(token=settings.bot_token)
    dp = Dispatcher()

    dp.update.middleware(DbSessionMiddleware())

    dp.include_router(start.router)
    dp.include_router(check.router)
    dp.include_router(voting.router)
    dp.include_router(admin.router)
    # Handlers for payment will be added in later tasks

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
