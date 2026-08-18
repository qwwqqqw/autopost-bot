"""Configuration and environment variables loader."""

import os
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path)


BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
CHANNEL_ID = os.getenv("CHANNEL_ID", "@my_channel_username")
DEFAULT_WATERMARK = os.getenv("DEFAULT_WATERMARK", "@MyChannel")
AI_API_KEY = os.getenv("AI_API_KEY", "").strip()

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "database" / "content_bot.db"
UPLOADS_DIR = BASE_DIR / "uploads"

NEWS_URL = "https://www.rbc.ru/life/tag/pets"
