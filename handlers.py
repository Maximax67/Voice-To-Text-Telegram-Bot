from aiogram import types
from aiogram.filters.command import Command
from aiogram.types.input_file import FSInputFile

from bot_init import dp, bot
from logger import logger
from api import process_request
from utils import get_bot_settings, check_if_admin, get_args_after_command, get_last_n_lines, send_long_message, send_message_to_admins
from config import COMMAND_TRANSCRIBE, COMMAND_DIARIZE, INSTANT_REPLY_IN_GROUPS, ADMIN_ID, LOG_FILENAME, MAX_MESSAGE_LENGTH


# Function to handle start commands
@dp.message(Command("start"))
async def transcribe_command(message: types.Message):
    user = message.from_user
    logger.info(f"User ID: {user.id}, Chat ID: {message.chat.id}, Username: {user.username}, Used start command")
    await message.reply(**get_bot_settings().as_kwargs())


# Function to handle help commands
@dp.message(Command("help"))
async def transcribe_command(message: types.Message):
    user = message.from_user
    logger.info(f"User ID: {user.id}, Chat ID: {message.chat.id}, Username: {user.username}, Used help command")
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
        logger.info(f"A | User ID: {user_id}, Chat ID: {chat_id}, Username: {user.username}, Tried to use admin logsfile command!")
        return

    if not LOG_FILENAME:
        logger.info(f"A | User ID: {user_id}, Chat ID: {chat_id}, Username: {user.username}, Can't get logs file, not saving in a file")
        await message.reply("Logs are not saving in file. Set LOG_FILENAME variable in .env!")
        return

    log_file = FSInputFile(LOG_FILENAME)
    try:
        await message.reply_document(log_file)
        logger.info(f"A | User ID: {user_id}, Chat ID: {chat_id}, Username: {user.username}, ALL logs sended!")
    except Exception as e:
        logger.error(f"A | User ID: {user_id}, Chat ID: {chat_id}, Username: {user.username}, Can't send logs file: {str(e)}")
        await message.reply("Can't send logs!")


# Function to handle logs commands
@dp.message(Command("logs"))
async def send_logs(message: types.Message):
    chat_id = message.chat.id
    user = message.from_user
    user_id = user.id

    if not check_if_admin(chat_id, user_id):
        logger.info(f"A | User ID: {user_id}, Chat ID: {chat_id}, Username: {user.username}, Tried to use admin logs command!")
        return

    if not LOG_FILENAME:
        logger.info(f"A | User ID: {user_id}, Chat ID: {chat_id}, Username: {user.username}, Can't get logs, not saving in a file")
        await message.reply("Logs are not saving in file. Set LOG_FILENAME variable in .env!")
        return

    text = message.text
    arg = get_args_after_command(text, "logs")

    # Check if the command has an argument
    if not arg:
        logger.info(f"A | User ID: {user_id}, Chat ID: {chat_id}, Username: {user.username}, Arguments not provided for logs!")
        await message.reply("Please provide N with the command in the format /logs N")
        return

    try:
        N = int(arg)
    except Exception:
        logger.info(f"A | User ID: {user_id}, Chat ID: {chat_id}, Username: {user.username}, Invalid N argument for logs: {arg}!")
        await message.reply("Invalid N in the format /logs N. Must be int! 1 <= N <= 100")
        return

    if N < 1 or N > 100:
        logger.info(f"A | User ID: {user_id}, Chat ID: {chat_id}, Username: {user.username}, Invalid N argument for logs: {N}!")
        await message.reply("Invalid N! 1 <= N <= 100")
        return

    result = get_last_n_lines(LOG_FILENAME, N)

    if not result:
        logger.error(f"A | User ID: {user_id}, Chat ID: {chat_id}, Username: {user.username}, Can't get {N} lines from log file!")
        await message.reply("Can't get logs")
        return

    str_result = '\n'.join(result)

    logger.info(f"A | User ID: {user_id}, Chat ID: {chat_id}, Username: {user.username}, Sended {N} last lines in log file!")
    if len(str_result) <= MAX_MESSAGE_LENGTH:
        await message.reply(str_result)
    else:
        await send_long_message(message, str_result)


# Function to handle file commands
@dp.message(Command("file"))
async def send_file(message: types.Message):
    chat_id = message.chat.id
    user = message.from_user
    user_id = user.id

    if not check_if_admin(chat_id, user_id):
        logger.info(f"A | User ID: {user_id}, Chat ID: {chat_id}, Username: {user.username}, Tried to use admin file command!")
        return

    # Extract the file_id from the command arguments
    text = message.text
    file_id = get_args_after_command(text, "file")

    # Check if the command has an argument
    if not file_id:
        logger.info(f"A | User ID: {user_id}, Chat ID: {chat_id}, Username: {user.username}, Arguments not provided for file!")
        await message.reply("Please provide a file_id with the command in the format /file file_id")
        return

    # Send the voice message to the chat where the command was sent
    try:
        await message.reply_document(file_id)
        logger.info(f"A | User ID: {user_id}, Chat ID: {chat_id}, Username: {user.username}, Sent file message: {file_id}")
    except Exception as e:
        logger.error(f"A | User ID: {user_id}, Chat ID: {chat_id}, Username: {user.username}, Error sending file message: {str(e)}")
        await message.reply("Error sending the file message! Check file id!")


# Function to handle broadcast commands
@dp.message(Command("adminbroadcast"))
async def admin_broadcast(message: types.Message):
    chat_id = message.chat.id
    user = message.from_user
    user_id = user.id

    if not check_if_admin(chat_id, user_id):
        logger.info(f"A | User ID: {user_id}, Chat ID: {chat_id}, Username: {user.username}, Tried to use admin broadcast command!")
        return

    if len(ADMIN_ID) < 2:
        logger.info(f"A | User ID: {user_id}, Chat ID: {chat_id}, Username: {user.username}, Can't admin broadcast, only one admin!")
        await message.reply("You can't broadcast messages as you are only one admin!")
        return

    # Extract the message from the command arguments
    text = message.text
    broadcast_message = get_args_after_command(text, "adminbroadcast")

    # Check if the command has an argument
    if not broadcast_message:
        logger.info(f"A | User ID: {user_id}, Chat ID: {chat_id}, Username: {user.username}, Arguments not provided for admin broadcast!")
        await message.reply("Please provide a message with the command in the format /adminbroadcast message")
        return

    me = []
    if user_id in ADMIN_ID:
        me.append(user_id)
    if chat_id != user_id and chat_id in ADMIN_ID:
        me.append(chat_id)

    if len(me) == len(ADMIN_ID):
        logger.info(f"A | User ID: {user_id}, Chat ID: {chat_id}, Username: {user.username}, Unimportant admin broadcast!")
        await message.reply("You don't need to make a broadcast as you can print message directly in this chat!")
        return

    # Send the broadcast message
    logger.info(f"A | User ID: {user_id}, Chat ID: {chat_id}, Username: {user.username}, Broadcasted: {broadcast_message}!")

    failed = await send_message_to_admins(broadcast_message, me)
    if failed:
        await message.reply(f"Could not broadcast for: {', '.join(str(item) for item in failed)}!\bBroadcasted to {len(ADMIN_ID) - len(failed) - 1}/{len(ADMIN_ID) - 1} admins and chat admins!")
    else:
        await message.reply(f"Broadcasted successfully to {len(ADMIN_ID) - 1} admins and chat admins!")


# Function to handle broadcast commands
@dp.message(Command("broadcast"))
async def broadcast(message: types.Message):
    chat_id = message.chat.id
    user = message.from_user
    user_id = user.id

    if not check_if_admin(chat_id, user_id):
        logger.info(f"A | User ID: {user_id}, Chat ID: {chat_id}, Username: {user.username}, Tried to use broadcast command!")
        return

    # Extract the message from the command arguments
    text = message.text
    args = get_args_after_command(text, "broadcast")
    if args:
        args = args.split(' ', 1)

    # Check if the command has arguments
    if not args or len(args) != 2 or not args[0] or not args[1]:
        logger.info(f"A | User ID: {user_id}, Chat ID: {chat_id}, Username: {user.username}, Arguments not provided for broadcast!")
        await message.reply("Please provide a message with the command in the format /broadcast id1,id2,id3 message")
        return

    ids, broadcast_message = args

    try:
        ids = [int(x) for x in ids.split(",")]
    except Exception:
        logger.info(f"A | User ID: {user_id}, Chat ID: {chat_id}, Username: {user.username}, Invalid broadcast ids: {ids}!")
        await message.reply("Invalid broadcast ids! Not int!")
        return

    # Send the broadcast message
    logger.info(f"A | User ID: {user_id}, Chat ID: {chat_id}, Username: {user.username}, Broadcasted: {broadcast_message}!")

    failed = []
    for id in ids:
        try:
            await bot.send_message(id, broadcast_message)
        except Exception as e:
            failed.append(id)
            logger.error(f"A | Message didn't broadcast to {id}: {str(e)}")

    if failed:
        await message.reply(f"Could not broadcast for: {', '.join(str(item) for item in failed)}!\bBroadcasted to {len(ADMIN_ID) - len(failed) - 1}/{len(ADMIN_ID) - 1} user and chats!")
    else:
        await message.reply(f"Broadcasted successfully to {len(ids)} users and chats!")


# Function to handle direct voice messages
@dp.message()
async def voice_message(message: types.Message):
    if message.content_type in {'voice', 'audio', 'video_note', 'video'}:
        if message.chat.type == 'private' or INSTANT_REPLY_IN_GROUPS:
            await process_request(message, False, False)
    elif message.chat.type == 'private':
        user = message.from_user
        logger.info(f"User ID: {user.id}, Chat ID: {message.chat.id}, Username: {user.username}, Sended invalid message: {message.message_id}")
        await message.reply(f"Send a voice, audio, video message or reply to it using commands! (see /help).")
