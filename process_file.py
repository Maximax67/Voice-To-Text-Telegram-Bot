from aiogram import types

from bot_init import bot
from logger import logger
from messages.log.file import *
from messages.log.other import INVALID_MESSAGE
from messages.telegram.file import *
from messages.telegram.other import TG_INVALID_MESSAGE_REPLY
from config import MAX_FILE_SIZE, MAX_DURATION_SECONDS, SUPPORTED_FILE_EXTENSIONS


async def get_file(message: types.Message, reply: bool):
    user = message.from_user
    username = user.username
    user_id = user.id
    chat_id = message.chat.id

    trigger_msg = message
    if reply:
        message = message.reply_to_message

    try:
        file = message.voice or message.audio or message.video_note or message.video if message else None
        if not file:
            logger.info(INVALID_MESSAGE.format(user_id, chat_id, username, trigger_msg.message_id))
            await trigger_msg.reply(TG_INVALID_MESSAGE_REPLY)
            return

        file_id = file.file_id
        logger.info(REQUESTED.format(user_id, chat_id, username, file_id))

        # Check file size
        if MAX_FILE_SIZE and file.file_size > MAX_FILE_SIZE:
            logger.info(SIZE_LIMIT.format(user_id, chat_id, username, file_id))
            await message.reply(TG_FILE_SIZE_LIMIT_EXCEED)
            return

        # Check file duration for voice messages
        if hasattr(file, "duration") and MAX_DURATION_SECONDS and file.duration > MAX_DURATION_SECONDS:
            logger.info(DURATION_LIMIT.format(user_id, chat_id, username, file_id))
            await message.reply(TG_FILE_DURATION_LIMIT_EXCEED)
            return

        # Request file path
        try:
            file_requested = await bot.get_file(file_id)
            file_path = file_requested.file_path

            # Double-Check file size
            if MAX_FILE_SIZE and file_requested.file_size > MAX_FILE_SIZE:
                logger.info(SIZE_LIMIT.format(user_id, chat_id, username, file_id))
                await message.reply(TG_FILE_SIZE_LIMIT_EXCEED)
                return
        except Exception as e:
            logger.error(REQUEST_ERROR.format(user_id, chat_id, username, file_id, str(e)))
            await message.reply(TG_FILE_REQUEST_ERROR)
            return

        # Check file extension
        last_dot_index = file_path.rfind('.')
        if last_dot_index == -1:
            logger.info(UNKNOWN_EXTENSION.format(user_id, chat_id, username, file_id))
            await message.reply(TG_FILE_EXTENSION_UNKNOWN)
            return

        file_extension = file_path[last_dot_index + 1:].lower()
        if not file_extension in SUPPORTED_FILE_EXTENSIONS:
            logger.info(UNSUPPORTED_FORMAT.format(user_id, chat_id, username, file_id, file_extension))
            await message.reply(TG_FILE_UNSUPPORTED_FORMAT.format(file_extension))
            return

        msg = await message.reply(TG_FILE_WAIT_DOWNLOAD)

        # Download the voice message
        try:
            file_content = await bot.download_file(file_path)
            data = file_content.read()
        except Exception as e:
            logger.error(DOWNLOAD_ERROR.format(user_id, chat_id, username, file_id, str(e)))
            await msg.edit_text(TG_FILE_DOWNLOAD_ERROR)
            return
    except Exception as e:
        logger.error(UNKNOWN_ERROR.format(user_id, chat_id, username, str(e)))
        await trigger_msg.reply(TG_FILE_ERROR)
        return

    return data, msg, file.file_id
