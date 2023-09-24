from aiogram import Bot, Dispatcher

from logger import logger
from messages.log.other import TELEGRAM_TOKEN_NOT_SET
from config import TELEGRAM_BOT_TOKEN


if not TELEGRAM_BOT_TOKEN:
    logger.error(TELEGRAM_TOKEN_NOT_SET)

bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()
