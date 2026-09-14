import os

from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
AI_PROVIDER = os.getenv("AI_PROVIDER", "anthropic")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

DB_PATH = os.getenv("DB_PATH", "data/bot.db")
CACHE_TTL_HOURS = int(os.getenv("CACHE_TTL_HOURS", "6"))
ANTI_FLOOD_COOLDOWN_SECONDS = int(os.getenv("ANTI_FLOOD_COOLDOWN_SECONDS", "5"))
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-5")
