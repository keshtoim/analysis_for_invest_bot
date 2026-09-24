import asyncio

from app.db.database import init_db
from app.loader import bot, dp
from app.handlers import register_handlers
from app.utils.logger import logger


async def on_startup() -> None:
    me = await bot.get_me()
    logger.info("Бот @%s запущен и слушает Telegram (long polling)", me.username)


async def main() -> None:
    await init_db()
    register_handlers(dp)
    dp.startup.register(on_startup)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
