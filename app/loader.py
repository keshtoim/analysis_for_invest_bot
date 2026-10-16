from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from app.config import BOT_TOKEN
from app.middlewares.blocked_user import BlockedUserMiddleware
from app.middlewares.maintenance import MaintenanceMiddleware
from app.middlewares.message_logger import MessageLoggingMiddleware

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()
# Логируем даже сообщения от заблокированных — история должна видеть попытки.
dp.message.middleware(MessageLoggingMiddleware())
dp.message.middleware(BlockedUserMiddleware())
dp.callback_query.middleware(BlockedUserMiddleware())
# После блокировки: заблокированный получает BLOCKED_TEXT, а не техработы —
# это точнее про его конкретную ситуацию.
dp.message.middleware(MaintenanceMiddleware())
dp.callback_query.middleware(MaintenanceMiddleware())
