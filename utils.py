import re
import asyncio
import contextvars
from functools import partial
from aiogram import types
from aiogram.utils.formatting import Text, Bold

from bot_init import bot
from logger import logger
from messages.log.handlers import ADMIN_BROADCAST_FAIL, ADMIN_BROADCAST_FORWARD_FAIL
from messages.log.other import LONG_MESSAGE_SEND_ERROR, LOG_FILE_NOT_FOUND, LOG_FILE_READ_ERROR, \
                                EDIT_MESSAGE_ERROR, SEND_MESSAGE_ERROR, REPLY_MESSAGE_ERROR
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


# Function to send the message
async def send_message(chat_id: int, text: str, parse_mode=None):
    try:
        msg = await bot.send_message(chat_id, text, parse_mode=parse_mode)
        return msg
    except Exception as e:
        logger.error(SEND_MESSAGE_ERROR.format(str(e)))


# Function to edit the message
async def edit_message(message: types.Message, text: str, parse_mode=None, send_new=True):
    try:
        msg = await message.edit_text(text, parse_mode=parse_mode)
        return msg
    except Exception as e:
        logger.error(EDIT_MESSAGE_ERROR.format(str(e)))

    if send_new:
        return await send_message(message.chat.id, text, parse_mode=parse_mode)


# Function to reply to the message
async def reply_message(message: types.Message, text: str, parse_mode=None, send_new=True):
    try:
        msg = await message.reply(text, parse_mode=parse_mode)
        return msg
    except Exception as e:
        logger.error(REPLY_MESSAGE_ERROR.format(str(e)))

    if send_new:
        return await send_message(message.chat.id, text, parse_mode=parse_mode)


# Check if message has not opened <code> tag
def is_first_code_tag_opened(message: str):
    # Find the first occurrence of </code>
    first_code_close = message.find("</code>")

    # If </code> is not found, return True
    if first_code_close == -1:
        return True

    # Find the corresponding <code> tag after before </code>
    first_code_start = message.find("<code>", 0, first_code_close)

    # If <code> is not found or is after the first </code>, return False
    if first_code_start == -1 or first_code_start > first_code_close:
        return False

    # If everything checks out, return True
    return True


# Check if message has not closed <code> tag
def is_last_code_tag_closed(message: str):
    # Find the last occurrence of <code> from the right
    last_code_start = message.rfind("<code>")

    # If <code> is not found, return True
    if last_code_start == -1:
        return True

    # Find the corresponding </code> tag after the last <code>
    last_code_end = message.find("</code>", last_code_start)

    # If </code> is not found or is before the last <code>, return False
    if last_code_end == -1 or last_code_end < last_code_start:
        return False

    # If everything checks out, return True
    return True


# Check if code tag is partially written
def code_tag_partial(message: str, is_start: bool):
    if is_start:
        brace_pos = message.find(">", 0, 5)
    else:
        brace_pos = message.find("<", len(message) - 6, len(message))

    if brace_pos != -1:
        return brace_pos

    return -1


# Function to send a long message split into multiple parts
async def send_long_message(msg: types.Message, text: str, new_reply=True, parse_mode=None):
    try:
        # Calculate the number of parts needed
        num_parts = (len(text) - 1) // MAX_MESSAGE_LENGTH + 1

        # Split the message into parts and send them as separate messages
        for i in range(num_parts):
            start_index = i * MAX_MESSAGE_LENGTH
            end_index = (i + 1) * MAX_MESSAGE_LENGTH
            part = text[start_index:end_index]

            if parse_mode == "HTML":
                if not is_first_code_tag_opened(part):
                    part = "<code>" + part
                partial = code_tag_partial(part, True)
                if partial != -1:
                    part = part[partial + 1:]
                partial = code_tag_partial(part, False)
                if partial != -1:
                    part = part[:partial] + "</code>"
                if not is_last_code_tag_closed(part):
                    part += "</code>"

            if i == 0:
                # Send the first part as a new message
                if new_reply:
                    msg_next = await reply_message(msg, part, parse_mode=parse_mode)
                else:
                    msg_next = await edit_message(msg, part, parse_mode=parse_mode)
            else:
                # Send subsequent parts as replies to the previous message
                msg_next = await reply_message(msg_next, part, parse_mode=parse_mode)
    except Exception as e:
        logger.error(LONG_MESSAGE_SEND_ERROR.format(str(e)))
        if "msg_next" in locals():
            await reply_message(msg_next, TG_LONG_MESSAGE_SEND_ERROR)
        else:
            await reply_message(msg, TG_LONG_MESSAGE_SEND_ERROR)


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
