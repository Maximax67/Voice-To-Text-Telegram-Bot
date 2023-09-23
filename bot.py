import asyncio

from logger import logger
from bot_init import bot, dp
from handlers import *
from api import diarize_queue_process, transcribe_queue_process

async def main():
    try:
        asyncio.create_task(diarize_queue_process())
        asyncio.create_task(transcribe_queue_process())
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"App Error: {str(e)}")

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
