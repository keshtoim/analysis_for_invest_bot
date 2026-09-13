import os

from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
AI_PROVIDER = os.getenv("AI_PROVIDER", "anthropic")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

DB_PATH = os.getenv("DB_PATH", "data/bot.db")
