import re
import asyncio
import contextvars
from functools import partial
from aiogram import types
from aiogram.utils.formatting import Text, Bold

from bot_init import bot
from logger import logger
from messages.log.handlers import ADMIN_BROADCAST_FAIL, ADMIN_BROADCAST_FORWARD_FAIL
from messages.log.other import LONG_MESSAGE_SEND_ERROR, LOG_FILE_NOT_FOUND, LOG_FILE_READ_ERROR
from messages.telegram.other import TG_LONG_MESSAGE_SEND_ERROR
from config import COMMAND_TRANSCRIBE, COMMAND_DIARIZE, INSTANT_REPLY_IN_GROUPS, ADMIN_ID, MAX_FILE_SIZE, \
                    MAX_DURATION_SECONDS, MAX_SIMULTANIOUS_REQUESTS, USER_RATE_LIMIT, USER_REQUEST_TIME, MAX_MESSAGE_LENGTH


# Add supports to python 3.7-3.8 (asyncio.to_thread)
# Copied from source code: https://github.com/python/cpython/blob/main/Lib/asyncio/threads.py#L12
async def to_thread(func, /, *args, **kwargs):
    loop = asyncio.get_running_loop()
    ctx = contextvars.copy_context()
    func_call = partial(ctx.run, func, *args, **kwargs)
    return await loop.run_in_executor(None, func_call)


# Function to send a long message split into multiple parts
async def send_long_message(msg: types.Message, text: str, new_reply=True):
    try:
        # Calculate the number of parts needed
        num_parts = (len(text) - 1) // MAX_MESSAGE_LENGTH + 1

        # Split the message into parts and send them as separate messages
        for i in range(num_parts):
            start_index = i * MAX_MESSAGE_LENGTH
            end_index = (i + 1) * MAX_MESSAGE_LENGTH
            part = text[start_index:end_index]

            if i == 0:
                # Send the first part as a new message
                if new_reply:
                    msg_next = await msg.reply(part)
                else:
                    msg_next = await msg.edit_text(part)
            else:
                # Send subsequent parts as replies to the previous message
                msg_next = await msg_next.reply(part)
    except Exception as e:
        logger.error(LONG_MESSAGE_SEND_ERROR.format(str(e)))
        if "msg_next" in locals():
            await msg_next.reply(TG_LONG_MESSAGE_SEND_ERROR)
        else:
            await msg.reply(TG_LONG_MESSAGE_SEND_ERROR)


# Function to get bot settings
def get_bot_settings():
    return Text("Transcribe command: ",
                Bold("/", COMMAND_TRANSCRIBE) if COMMAND_TRANSCRIBE else Bold("not set"),
                "\nDiarize command: ",
                Bold("/", COMMAND_DIARIZE) if COMMAND_DIARIZE else Bold("not set"),
                "\n\nMax file size: ",
                Bold('{:.1f}'.format(MAX_FILE_SIZE / (1024 * 1024)), " MB") if MAX_FILE_SIZE else Bold("unlimited"),
                "\nMax duration: ",
                Bold(MAX_DURATION_SECONDS, " seconds") if MAX_DURATION_SECONDS else Bold("unlimited"),
                "\n\nInstant reply in groups: ",
                Bold("enabled" if INSTANT_REPLY_IN_GROUPS else "disabled"),
                "\nMax simultaneous requests: ",
                Bold(MAX_SIMULTANIOUS_REQUESTS),
                "\nUser requests rate limit: ",
                Bold(USER_RATE_LIMIT if USER_RATE_LIMIT else "unlimited"),
                "\nUser requests rate time: ",
                Bold(USER_REQUEST_TIME, " seconds") if USER_REQUEST_TIME else Bold("unlimited"),
                "\n", "-" * 30,
                "\nSend a voice, audio, video message or reply to it using commands!"
            )


# Check if chat_id or user_id in ADMIN_ID
def check_if_admin(chat_id: int, user_id: int):
    if ADMIN_ID:
        if chat_id in ADMIN_ID or user_id in ADMIN_ID:
            return True

    return False


# Get last n lines from file
def get_last_n_lines(filename: str, n: int):
    try:
        with open(filename, 'r', encoding="utf-8") as file:
            lines = file.readlines()
            if n >= len(lines):
                return lines
            else:
                return lines[-n:]
    except FileNotFoundError:
        logger.error(LOG_FILE_NOT_FOUND)
        return []
    except Exception as e:
        logger.error(LOG_FILE_READ_ERROR.format(n, str(e)))
        return []


# Get text after command
def get_args_after_command(text: str, command: str):
    command_substr = f"/{command} "
    if len(text) <= len(command_substr) or not text.startswith(command_substr):
        return

    return text[len(command_substr):]


# Send message to all admins
async def send_message_to_admins(text: str, skip: list[int]):
    if not ADMIN_ID:
        return []

    failed = []
    for admin in ADMIN_ID:
        if admin in skip:
            continue

        try:
            await bot.send_message(admin, text)
            await asyncio.sleep(0.1)
        except Exception as e:
            failed.append(admin)
            logger.error(ADMIN_BROADCAST_FAIL.format(admin, str(e)))

    return failed


# Forward message to all admins
async def forward_message_to_admins(message: types.Message, skip: list[int]):
    if not ADMIN_ID:
        return []

    failed = []
    for admin in ADMIN_ID:
        if admin in skip:
            continue

        try:
            await message.forward(admin)
            await asyncio.sleep(0.1)
        except Exception as e:
            failed.append(admin)
            logger.error(ADMIN_BROADCAST_FORWARD_FAIL.format(admin, str(e)))

    return failed


# Highlight important parts of logs with monospace (code) style
def logs_formatter(logs: list[str]):
    # Define a regular expression pattern for finding parts to highlight
    pattern = r'(User ID:|Chat ID:|Username:|File:|Requested:) ([\w-]+)'

    # Define a regular expression pattern for wrapping result and broadcasted texts
    result_pattern = r'(Result:|Broadcasted:) (.+)'

    for i in range(len(logs)):
        # Find and format matches in the log message
        logs[i] = re.sub(pattern, r'\1 <code>\2</code>', logs[i])
        logs[i] = re.sub(result_pattern, r'\1 <code>\2</code>', logs[i])