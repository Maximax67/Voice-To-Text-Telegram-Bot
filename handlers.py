import asyncio
from aiogram import types
from aiogram.filters.command import Command
from aiogram.types.input_file import FSInputFile

from bot_init import dp, bot
from logger import logger
from messages.log.handlers import *
from messages.log.other import INVALID_MESSAGE
from messages.telegram.handlers import *
from messages.telegram.other import TG_INVALID_MESSAGE_DIRECT
from api import process_request
from utils import get_bot_settings, check_if_admin, get_args_after_command, get_last_n_lines,\
                    send_long_message, send_message_to_admins, forward_message_to_admins, logs_formatter
from config import COMMAND_TRANSCRIBE, COMMAND_DIARIZE, INSTANT_REPLY_IN_GROUPS, \
                    ADMIN_ID, LOG_FILENAME, MAX_MESSAGE_LENGTH


# Function to handle start commands
@dp.message(Command("start"))
async def transcribe_command(message: types.Message):
    user = message.from_user
    logger.info(START_COMMAND.format(user.id, message.chat.id, user.username))
    await message.reply(**get_bot_settings().as_kwargs())


# Function to handle help commands
@dp.message(Command("help"))
async def transcribe_command(message: types.Message):
    user = message.from_user
    logger.info(HELP_COMMAND.format(user.id, message.chat.id, user.username))
    await message.reply(**get_bot_settings().as_kwargs())


# Function to handle COMMAND_TRANSCRIBE
@dp.message(Command(COMMAND_TRANSCRIBE))
async def transcribe_command(message: types.Message):
    await process_request(message, True, False)


# Function to handle COMMAND_DIARIZE
@dp.message(Command(COMMAND_DIARIZE))
async def diarize_command(message: types.Message):
    await process_request(message, True, True)


# Function to handle logsfile commands
@dp.message(Command("logsfile"))
async def send_logs_file(message: types.Message):
    chat_id = message.chat.id
    user = message.from_user
    user_id = user.id

    if not check_if_admin(chat_id, user_id):
        logger.info(LOGSFILE_NOT_ADMIN.format(user_id, chat_id, user.username))
        return

    if not LOG_FILENAME:
        logger.info(LOGSFILE_NOT_SAVING.format(user_id, chat_id, user.username))
        await message.reply(TG_LOGS_NOT_SAVING_IN_FILE)
        return

    log_file = FSInputFile(LOG_FILENAME)
    try:
        await message.reply_document(log_file)
        logger.info(LOGSFILE_SEND.format(user_id, chat_id, user.username))
    except Exception as e:
        logger.error(LOGSFILE_SEND_ERROR.format(user_id, chat_id, user.username, str(e)))
        await message.reply(TG_LOGS_SEND_ERROR)


# Function to handle logs commands
@dp.message(Command("logs"))
async def send_logs(message: types.Message):
    chat_id = message.chat.id
    user = message.from_user
    user_id = user.id

    if not check_if_admin(chat_id, user_id):
        logger.info(LOGS_NOT_ADMIN.format(user_id, chat_id, user.username))
        return

    if not LOG_FILENAME:
        logger.info(LOGS_NOT_SAVING.format(user_id, chat_id, user.username))
        await message.reply(TG_LOGS_NOT_SAVING_IN_FILE)
        return

    text = message.text
    arg = get_args_after_command(text, "logs")

    # Check if the command has an argument
    if not arg:
        logger.info(LOGS_NO_ARGS.format(user_id, chat_id, user.username))
        await message.reply(TG_LOGS_INVALID_FORMAT)
        return

    try:
        N = int(arg)
    except Exception:
        logger.info(LOGS_INVALID_N.format(user_id, chat_id, user.username, N))
        await message.reply(TG_LOGS_INVALID_N)
        return

    if N < 1 or N > 100:
        logger.info(LOGS_INVALID_N_VALUE.format(user_id, chat_id, user.username, N))
        await message.reply(TG_LOGS_INVALID_N_VALUE)
        return

    result = get_last_n_lines(LOG_FILENAME, N)
    logs_formatter(result)

    if not result:
        logger.error(LOGS_GET_ERROR.format(user_id, chat_id, user.username, N))
        await message.reply(TG_LOGS_GET_ERROR)
        return

    str_result = '\n'.join(result)

    logger.info(LOGS_SEND.format(user_id, chat_id, user.username, N))
    if len(str_result) <= MAX_MESSAGE_LENGTH:
        await message.reply(str_result, parse_mode="HTML")
    else:
        await send_long_message(message, str_result)


# Function to handle file commands
@dp.message(Command("file"))
async def send_file(message: types.Message):
    chat_id = message.chat.id
    user = message.from_user
    user_id = user.id

    if not check_if_admin(chat_id, user_id):
        logger.info(FILE_NOT_ADMIN.format(user_id, chat_id, user.username))
        return

    # Extract the file_id from the command arguments
    text = message.text
    file_id = get_args_after_command(text, "file")

    # Check if the command has an argument
    if not file_id:
        logger.info(FILE_NOT_ARGS.format(user_id, chat_id, user.username))
        await message.reply(TG_FILE_INVALID_FORMAT)
        return

    # Send the voice message to the chat where the command was sent
    try:
        await message.reply_document(file_id)
        logger.info(FILE_SEND.format(user_id, chat_id, user.username, file_id))
    except Exception as e:
        logger.error(FILE_SEND_ERROR.format(user_id, chat_id, user.username, file_id, str(e)))
        await message.reply(TG_FILE_SEND_ERROR)


# Function to handle broadcast commands
@dp.message(Command("adminbroadcast"))
async def admin_broadcast(message: types.Message):
    chat_id = message.chat.id
    user = message.from_user
    user_id = user.id

    if not check_if_admin(chat_id, user_id):
        logger.info(ADMIN_BROADCAST_NOT_ADMIN.format(user_id, chat_id, user.username))
        return

    if len(ADMIN_ID) < 2:
        logger.info(ADMIN_BROADCAST_ONE_ADMIN.format(user_id, chat_id, user.username))
        await message.reply(TG_ADMIN_BROADCAST_ONE_ADMIN)
        return

    # Extract the message from the command arguments
    text = message.text
    broadcast_message = get_args_after_command(text, "adminbroadcast")

    replied = message.reply_to_message

    # Check if the command has an argument
    if not broadcast_message and not replied:
        logger.info(ADMIN_BROADCAST_NO_ARGS.format(user_id, chat_id, user.username))
        await message.reply(TG_ADMIN_BROADCAST_INVALID_FORMAT)
        return

    me = []
    if user_id in ADMIN_ID:
        me.append(user_id)
    if chat_id != user_id and chat_id in ADMIN_ID:
        me.append(chat_id)

    if len(me) == len(ADMIN_ID):
        logger.info(ADMIN_BROADCAST_UNIMPORTANT.format(user_id, chat_id, user.username))
        await message.reply(TG_ADMIN_BROADCAST_UNIMPORTANT)
        return

    # Send the broadcast message
    logger.info(ADMIN_BROADCAST_MESSAGE.format(user_id, chat_id, user.username, broadcast_message))

    if broadcast_message:
        failed = await send_message_to_admins(broadcast_message, me)
        if failed:
            await message.reply(TG_ADMIN_BROADCAST_FAIL.format(', '.join(str(item) for item in failed), len(ADMIN_ID) - len(failed) - 1, len(ADMIN_ID) - 1))
        else:
            await message.reply(TG_ADMIN_BROADCAST_SUCCESS.format(len(ADMIN_ID) - 1))

    if replied:
        failed = await forward_message_to_admins(replied, me)
        if failed:
            await message.reply(TG_ADMIN_BROADCAST_FORWARD_FAIL.format(', '.join(str(item) for item in failed), len(ADMIN_ID) - len(failed) - 1, len(ADMIN_ID) - 1))
        else:
            await message.reply(TG_ADMIN_BROADCAST_FORWARD_SUCCESS.format(len(ADMIN_ID) - 1))


# Function to handle broadcast commands
@dp.message(Command("broadcast"))
async def broadcast(message: types.Message):
    chat_id = message.chat.id
    user = message.from_user
    user_id = user.id

    if not check_if_admin(chat_id, user_id):
        logger.info(BROADCAST_NOT_ADMIN.format(user_id, chat_id, user.username))
        return

    # Extract the message from the command arguments
    text = message.text
    args = get_args_after_command(text, "broadcast")
    if args:
        args = args.split(' ', 1)

    replied = message.reply_to_message

    # Check if the command has arguments
    if not args or (not replied and len(args) == 1):
        logger.info(BROADCAST_NO_ARGS.format(user_id, chat_id, user.username))
        await message.reply(TG_BROADCAST_INVALID_FORMAT)
        return

    ids = args[0]

    try:
        ids = [int(x) for x in ids.split(",")]
    except Exception:
        logger.info(BROADCAST_ID_ERROR.format(user_id, chat_id, user.username, ids))
        await message.reply(TG_BROADCAST_INVALID_IDS)
        return

    broadcast_message = None
    if len(args) == 2:
        broadcast_message = args[1]
        logger.info(BROADCAST_MESSAGE.format(user_id, chat_id, user.username, broadcast_message))

    # Send the broadcast message
    if broadcast_message:
        failed = []
        for id in ids:
            try:
                await bot.send_message(id, broadcast_message)
                await asyncio.sleep(0.1)
            except Exception as e:
                failed.append(id)
                logger.error(BROADCAST_FAIL.format(id, str(e)))

        if failed:
            await message.reply(TG_BROADCAST_FAIL.format(', '.join(str(item) for item in failed), len(ids) - len(failed), len(ids)))
        else:
            await message.reply(TG_BROADCAST_SUCCESS.format(len(ids)))

    # Forward replied message
    if replied:
        failed_forward = []
        for id in ids:
            try:
                await message.forward(id)
                await asyncio.sleep(0.1)
            except Exception as e:
                failed_forward.append(id)
                logger.error(BROADCAST_FORWARD_FAIL.format(id, str(e)))

        if failed_forward:
            await message.reply(TG_BROADCAST_FORWARD_FAIL.format(', '.join(str(item) for item in failed), len(ids) - len(failed), len(ids)))
        else:
            await message.reply(TG_BROADCAST_FORWARD_SUCCESS.format(len(ids)))


# Function to handle direct voice messages
@dp.message()
async def voice_message(message: types.Message):
    if message.content_type in {'voice', 'audio', 'video_note', 'video'}:
        if message.chat.type == 'private' or INSTANT_REPLY_IN_GROUPS:
            await process_request(message, False, False)
    elif message.chat.type == 'private':
        user = message.from_user
        logger.info(INVALID_MESSAGE.format(user.id, message.chat.id, user.username, message.message_id))
        await message.reply(TG_INVALID_MESSAGE_DIRECT)
