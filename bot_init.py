from aiogram import Bot, Dispatcher

from logger import logger
from config import TELEGRAM_BOT_TOKEN


if not TELEGRAM_BOT_TOKEN:
    logger.error("TELEGRAM_BOT_TOKEN not set! App will crash soon...")

bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()
