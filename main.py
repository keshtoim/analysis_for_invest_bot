import asyncio

from app.loader import bot, dp
from app.handlers import register_handlers


async def main() -> None:
    register_handlers(dp)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
