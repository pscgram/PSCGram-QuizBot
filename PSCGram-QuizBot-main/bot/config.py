import os
from dotenv import load_dotenv
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_IDS = {int(x.strip()) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip().lstrip("-").isdigit()}
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///pscgram.db")
PDF_CHANNEL_ID = os.getenv("PDF_CHANNEL_ID", "").strip()
DEFAULT_QUIZ_QUESTIONS = max(1, int(os.getenv("DEFAULT_QUIZ_QUESTIONS", "10")))
DEFAULT_TEST_MINUTES = max(1, int(os.getenv("DEFAULT_TEST_MINUTES", "15")))
PREMIUM_CURRENCY = os.getenv("PREMIUM_CURRENCY", "XTR")
PREMIUM_PRICE_STARS = max(1, int(os.getenv("PREMIUM_PRICE_STARS", "500")))
