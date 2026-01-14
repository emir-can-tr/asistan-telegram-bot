"""Konfigurasyon - VDS icin Local API destegi (OpenAI uyumlu)"""
import os
from dotenv import load_dotenv

load_dotenv()

# Telegram Bot
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# API Ayarlari - Local veya Gemini
API_MODE = os.getenv("API_MODE", "local")  # "local" veya "gemini"

# Local API (OpenAI uyumlu)
LOCAL_API_URL = os.getenv("LOCAL_API_URL", "http://127.0.0.1:8045/v1")
LOCAL_API_KEY = os.getenv("LOCAL_API_KEY", "sk-no-key-required")
LOCAL_MODEL_NAME = os.getenv("LOCAL_MODEL_NAME", "gpt-3.5-turbo")

# Gemini API (opsiyonel)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# Hatirlatma ayarlari
REMINDER_START_HOUR = int(os.getenv("REMINDER_START_HOUR", "8"))
REMINDER_END_HOUR = int(os.getenv("REMINDER_END_HOUR", "22"))
REMINDER_ENABLED = os.getenv("REMINDER_ENABLED", "true").lower() == "true"

# Timezone
TIMEZONE = os.getenv("TIMEZONE", "Europe/Istanbul")

# Database path
DATABASE_PATH = os.path.join(os.path.dirname(__file__), "asistan.db")
