from aiogram import Bot, Dispatcher

from app.config import BOT_TOKEN
from app.middlewares.anti_flood import AntiFloodMiddleware

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
dp.message.middleware(AntiFloodMiddleware())
