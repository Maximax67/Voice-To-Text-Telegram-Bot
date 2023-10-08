import asyncio
from aiogram import types
from aiogram.filters.command import Command
from aiogram.types.input_file import FSInputFile
from functools import wraps

from bot_init import dp, bot
from logger import logger
from messages.log.handlers import *
from messages.log.other import INVALID_MESSAGE
from messages.telegram.handlers import *
from messages.telegram.other import TG_INVALID_MESSAGE_DIRECT
from api import process_request
from utils import get_bot_settings, check_if_admin, get_args_after_command, get_last_n_lines,\
                    send_long_message, send_message_to_admins, forward_message_to_admins,\
                    logs_formatter, reply_message
from config import COMMAND_TRANSCRIBE, COMMAND_DIARIZE, INSTANT_REPLY_IN_GROUPS, \
                    ADMIN_ID, LOG_FILENAME, MAX_MESSAGE_LENGTH


disabled = False
disabled_semaphore = asyncio.Semaphore(1)


# Function to get disabled status
async def is_disabled():
    async with disabled_semaphore:
        global disabled
        return disabled


# Function to bypass disabled status
# 1 - Bot enabled
# 2 - Bot disabled, admin bypass
# 0 - Bot disabled, you are not admin
async def disable_bypass(user_id: int, chat_id: int):
    dis = await is_disabled()
    if not dis:
        return 1

    if check_if_admin(chat_id, user_id):
        return 2

    return 0


# Function to check if bot is disabled and bypass only admins
def disabled_check():
    def decorator(func):
        @wraps(func)
        async def wrapper(*args):
            message = args[0]
            chat_id = message.chat.id
            user = message.from_user
            user_id = user.id

            bypass = await disable_bypass(user_id, chat_id)
            if not bypass:
                logger.info(DISABLED.format(user_id, chat_id, user.username))
                return

            if bypass == 2:
                logger.info(DISABLED_BYPASS.format(user_id, chat_id, user.username))

            return await func(*args)
        return wrapper
    return decorator


# Function to handle start commands
@dp.message(Command("start"))
@disabled_check()
async def transcribe_command(message: types.Message):
    user = message.from_user
    logger.info(START_COMMAND.format(user.id, message.chat.id, user.username))
    await message.reply(**get_bot_settings().as_kwargs())


# Function to handle help commands
@dp.message(Command("help"))
@disabled_check()
async def transcribe_command(message: types.Message):
    user = message.from_user
    logger.info(HELP_COMMAND.format(user.id, message.chat.id, user.username))
    await message.reply(**get_bot_settings().as_kwargs())


# Function to handle COMMAND_TRANSCRIBE
@dp.message(Command(COMMAND_TRANSCRIBE))
@disabled_check()
async def transcribe_command(message: types.Message):
    await process_request(message, True, False)


# Function to handle COMMAND_DIARIZE
@dp.message(Command(COMMAND_DIARIZE))
@disabled_check()
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
        await reply_message(message, TG_LOGS_NOT_SAVING_IN_FILE)
        return

    log_file = FSInputFile(LOG_FILENAME)
    try:
        await message.reply_document(log_file)
        logger.info(LOGSFILE_SEND.format(user_id, chat_id, user.username))
    except Exception as e:
        logger.error(LOGSFILE_SEND_ERROR.format(user_id, chat_id, user.username, str(e)))
        await reply_message(message, TG_LOGS_SEND_ERROR)


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
        await reply_message(message, TG_LOGS_NOT_SAVING_IN_FILE)
        return

    text = message.text
    arg = get_args_after_command(text, "logs")

    # Check if the command has an argument
    if not arg:
        logger.info(LOGS_NO_ARGS.format(user_id, chat_id, user.username))
        await reply_message(message, TG_LOGS_INVALID_FORMAT)
        return

    try:
        N = int(arg)
    except Exception:
        logger.info(LOGS_INVALID_N.format(user_id, chat_id, user.username, N))
        await reply_message(message, TG_LOGS_INVALID_N)
        return

    if N < 1 or N > 100:
        logger.info(LOGS_INVALID_N_VALUE.format(user_id, chat_id, user.username, N))
        await reply_message(message, TG_LOGS_INVALID_N_VALUE)
        return

    result = get_last_n_lines(LOG_FILENAME, N)
    logs_formatter(result)

    if not result:
        logger.error(LOGS_GET_ERROR.format(user_id, chat_id, user.username, N))
        await reply_message(message, TG_LOGS_GET_ERROR)
        return

    str_result = '\n'.join(result)

    logger.info(LOGS_SEND.format(user_id, chat_id, user.username, N))
    if len(str_result) <= MAX_MESSAGE_LENGTH:
        await reply_message(message, str_result, parse_mode="HTML")
    else:
        await send_long_message(message, str_result, parse_mode="HTML")


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
        await reply_message(message, TG_FILE_INVALID_FORMAT)
        return

    # Send the voice message to the chat where the command was sent
    try:
        await message.reply_document(file_id)
        logger.info(FILE_SEND.format(user_id, chat_id, user.username, file_id))
    except Exception as e:
        logger.error(FILE_SEND_ERROR.format(user_id, chat_id, user.username, file_id, str(e)))
        await reply_message(message, TG_FILE_SEND_ERROR)


# Function to handle admin broadcast commands
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
        await reply_message(message, TG_ADMIN_BROADCAST_ONE_ADMIN)
        return

    # Extract the message from the command arguments
    text = message.text
    broadcast_message = get_args_after_command(text, "adminbroadcast")

    replied = message.reply_to_message

    # Check if the command has an argument
    if not broadcast_message and not replied:
        logger.info(ADMIN_BROADCAST_NO_ARGS.format(user_id, chat_id, user.username))
        await reply_message(message, TG_ADMIN_BROADCAST_INVALID_FORMAT)
        return

    me = []
    if user_id in ADMIN_ID:
        me.append(user_id)
    if chat_id != user_id and chat_id in ADMIN_ID:
        me.append(chat_id)

    if len(me) == len(ADMIN_ID):
        logger.info(ADMIN_BROADCAST_UNIMPORTANT.format(user_id, chat_id, user.username))
        await reply_message(message, TG_ADMIN_BROADCAST_UNIMPORTANT)
        return

    if broadcast_message:
        logger.info(ADMIN_BROADCAST_MESSAGE.format(user_id, chat_id, user.username, broadcast_message))
    if replied:
        logger.info(ADMIN_BROADCAST_FORWARD.format(user_id, chat_id, user.username))

    # Send the broadcast message
    if broadcast_message:
        failed = await send_message_to_admins(broadcast_message, me)
        if failed:
            await reply_message(message, TG_ADMIN_BROADCAST_FAIL.format(', '.join(str(item) for item in failed), len(ADMIN_ID) - len(failed) - 1, len(ADMIN_ID) - 1))
        else:
            await reply_message(message, TG_ADMIN_BROADCAST_SUCCESS.format(len(ADMIN_ID) - 1))

    if replied:
        failed = await forward_message_to_admins(replied, me)
        if failed:
            await reply_message(message, TG_ADMIN_BROADCAST_FORWARD_FAIL.format(', '.join(str(item) for item in failed), len(ADMIN_ID) - len(failed) - 1, len(ADMIN_ID) - 1))
        else:
            await reply_message(message, TG_ADMIN_BROADCAST_FORWARD_SUCCESS.format(len(ADMIN_ID) - 1))


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
        await reply_message(message, TG_BROADCAST_INVALID_FORMAT)
        return

    ids = args[0]

    try:
        ids = [int(x) for x in ids.split(",")]
    except Exception:
        logger.info(BROADCAST_ID_ERROR.format(user_id, chat_id, user.username, ids))
        await reply_message(message, TG_BROADCAST_INVALID_IDS)
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
            await reply_message(message, TG_BROADCAST_FAIL.format(', '.join(str(item) for item in failed), len(ids) - len(failed), len(ids)))
        else:
            await reply_message(message, TG_BROADCAST_SUCCESS.format(len(ids)))

    # Forward replied message
    if replied:
        logger.info(BROADCAST_FORWARD.format(user_id, chat_id, user.username))
        failed_forward = []
        for id in ids:
            try:
                await message.forward(id)
                await asyncio.sleep(0.1)
            except Exception as e:
                failed_forward.append(id)
                logger.error(BROADCAST_FORWARD_FAIL.format(id, str(e)))

        if failed_forward:
            await reply_message(message, TG_BROADCAST_FORWARD_FAIL.format(', '.join(str(item) for item in failed), len(ids) - len(failed), len(ids)))
        else:
            await reply_message(message, TG_BROADCAST_FORWARD_SUCCESS.format(len(ids)))


# Function to handle chatid commands
@dp.message(Command("chatid"))
async def get_chat_id(message: types.Message):
    chat_id = message.chat.id
    user = message.from_user
    user_id = user.id

    if not check_if_admin(chat_id, user_id):
        logger.info(GET_CHAT_ID_NOT_ADMIN.format(user_id, chat_id, user.username))
        return

    logger.info(GET_CHAT_ID_INFO.format(user_id, chat_id, user.username))
    await reply_message(message, TG_GET_CHAT_ID_INFO.format(chat_id), parse_mode="HTML")


# Function to handle disable commands
@dp.message(Command("disable"))
async def get_chat_id(message: types.Message):
    chat_id = message.chat.id
    user = message.from_user
    user_id = user.id

    if not check_if_admin(chat_id, user_id):
        logger.info(DISABLE_NOT_ADMIN.format(user_id, chat_id, user.username))
        return

    async with disabled_semaphore:
        global disabled
        if disabled:
            logger.info(DISABLE_WHEN_DISABLED.format(user_id, chat_id, user.username))
            await reply_message(message, TG_DISABLE_WHEN_DISABLED)
        else:
            disabled = True
            logger.info(DISABLE_SUCCESS.format(user_id, chat_id, user.username))
            await reply_message(message, TG_DISABLE_SUCCESS)


# Function to handle enable commands
@dp.message(Command("enable"))
async def get_chat_id(message: types.Message):
    chat_id = message.chat.id
    user = message.from_user
    user_id = user.id

    if not check_if_admin(chat_id, user_id):
        logger.info(ENABLE_NOT_ADMIN.format(user_id, chat_id, user.username))
        return

    async with disabled_semaphore:
        global disabled
        if disabled:
            disabled = False
            logger.info(ENABLE_SUCCESS.format(user_id, chat_id, user.username))
            await reply_message(message, TG_ENABLE_SUCCESS)
        else:
            logger.info(ENABLE_WHEN_ENABLED.format(user_id, chat_id, user.username))
            await reply_message(message, TG_ENABLE_WHEN_ENABLED)


# Function to handle all messages
@dp.message()
async def all_messages(message: types.Message):
    user = message.from_user
    if message.content_type in {'voice', 'audio', 'video_note', 'video', 'document'}:
        if message.chat.type == 'private' or INSTANT_REPLY_IN_GROUPS:
            bypass = await disable_bypass(user.id, message.chat.id)
            if not bypass:
                return

            if bypass == 2:
                logger.info(DISABLED_BYPASS.format(user.id, message.chat.id, user.username))
            await process_request(message, False, False)
    elif message.chat.type == 'private':
        bypass = await disable_bypass(user.id, message.chat.id)
        if not bypass:
            return

        if bypass == 2:
            logger.info(DISABLED_BYPASS.format(user.id, message.chat.id, user.username))
        logger.info(INVALID_MESSAGE.format(user.id, message.chat.id, user.username, message.message_id))
        await reply_message(message, TG_INVALID_MESSAGE_DIRECT)
