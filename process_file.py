from aiogram import types

from bot_init import bot
from logger import logger
from config import COMMAND_DIARIZE, COMMAND_TRANSCRIBE, MAX_FILE_SIZE, \
                    MAX_DURATION_SECONDS, SUPPORTED_FILE_EXTENSIONS


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
            logger.info(f"User ID: {user_id}, Chat ID: {chat_id}, Username: {username}, Invalid message: {trigger_msg.message_id}")
            await trigger_msg.reply(f"Please reply to a voice, audio, video message with /{COMMAND_DIARIZE} or /{COMMAND_TRANSCRIBE}")
            return

        logger.info(f"User ID: {user_id}, Chat ID: {chat_id}, Username: {username}, Requested: {file.file_id}")

        file_id = file.file_id

        # Check file size
        if MAX_FILE_SIZE and file.file_size > MAX_FILE_SIZE:
            logger.info(f"User ID: {user_id}, Chat ID: {chat_id}, Username: {username}, File: {file_id}, File exceeds size the limit")
            await message.reply(f"File size exceeds the {MAX_FILE_SIZE / (1024 * 1024):.1f} MB limit! Please send a smaller file.")
            return

        # Check file duration for voice messages
        if hasattr(file, "duration") and MAX_DURATION_SECONDS and file.duration > MAX_DURATION_SECONDS:
            logger.info(f"User ID: {user_id}, Chat ID: {chat_id}, Username: {username}, File: {file_id}, Duration exceeds the limit")
            await message.reply(f"Duration exceeds the {MAX_DURATION_SECONDS} seconds limit! Please send a shorter version!")
            return

        # Request file path
        try:
            file_requested = await bot.get_file(file_id)
            file_path = file_requested.file_path

            # Double-Check file size
            if MAX_FILE_SIZE and file_requested.file_size > MAX_FILE_SIZE:
                logger.info(f"User ID: {user_id}, Chat ID: {chat_id}, Username: {username}, File: {file_id}, File exceeds size the limit")
                await message.reply(f"File size exceeds the {MAX_FILE_SIZE / (1024 * 1024):.1f} MB limit! Please send a smaller file.")
                return
        except Exception as e:
            logger.error(f"User ID: {user_id}, Chat ID: {chat_id}, Username: {username}, Can't request file: {file_id}, {str(e)}")
            await message.reply("Error requesting file data!")
            return

        # Check file extension
        last_dot_index = file_path.rfind('.')
        if last_dot_index == -1:
            logger.info(f"User ID: {user_id}, Chat ID: {chat_id}, Username: {username}, File: {file_id}, Unknown file extension")
            await message.reply("Unknown file extension!")
            return

        file_extension = file_path[last_dot_index + 1:].lower()
        if not file_extension in SUPPORTED_FILE_EXTENSIONS:
            logger.info(f"User ID: {user_id}, Chat ID: {chat_id}, Username: {username}, File: {file_id}, Unsupported file format: {file_extension}")
            await message.reply(f"Unsupported file format: {file_extension}")
            return

        msg = await message.reply("Downloading file...")

        # Download the voice message
        try:
            file_content = await bot.download_file(file_path)
            data = file_content.read()
        except Exception as e:
            logger.error(f"User ID: {user_id}, Chat ID: {chat_id}, Username: {username}, Error downloading: {file_id}, {str(e)}")
            await msg.edit_text("Error downloading the file!")
            return
    except Exception as e:
        logger.error(f"User ID: {user_id}, Chat ID: {chat_id}, Username: {username}, Error: {str(e)}")
        await trigger_msg.reply(f"Error happened!")
        return

    return data, msg, file.file_id
