import os
import logging
import asyncio
import base64
import contextvars
import time
from collections import defaultdict, deque
from functools import partial, wraps
from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command
from aiogram.utils.formatting import Text, Bold
from gradio_client import Client
from dotenv import load_dotenv

# Load .env variables
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

COMMAND_TRANSCRIBE = os.getenv('COMMAND_TRANSCRIBE')
COMMAND_DIARIZE = os.getenv('COMMAND_DIARIZE')
INSTANT_REPLY_IN_GROUPS = bool(os.getenv('INSTANT_REPLY_IN_GROUPS'))
API_URL_TRANSCRIBE = os.getenv('API_URL_TRANSCRIBE')
API_URL_DIARIZE = os.getenv('API_URL_DIARIZE')
HF_TOKEN_TRANSCRIBE = os.getenv('HF_TOKEN_TRANSCRIBE')
HF_TOKEN_DIARIZE = os.getenv('HF_TOKEN_DIARIZE')

LOG_FILENAME = os.getenv('LOG_FILENAME')
LOG_FORMAT = os.getenv('LOG_FORMAT')

MAX_FILE_SIZE = os.getenv('MAX_FILE_SIZE')
MAX_DURATION_SECONDS = os.getenv('MAX_DURATION_SECONDS')

MAX_SIMULTANIOUS_REQUESTS = os.getenv('MAX_SIMULTANIOUS_REQUESTS')

USER_RATE_LIMIT = os.getenv('USER_RATE_LIMIT')
USER_REQUEST_TIME = os.getenv('USER_REQUEST_TIME')

SUPPORTED_FILE_EXTENSIONS = ('mid', 'mp3', 'opus', 'oga', 'ogg', 'wav', 'webm', 'weba', 'flac',
                        'wma', 'aiff', 'opus', 'm4a', 'au', 'mp4', 'avi', 'mkv', 'mov')

if MAX_FILE_SIZE:
    MAX_FILE_SIZE = float(MAX_FILE_SIZE) * 1024 * 1024

if MAX_DURATION_SECONDS:
    MAX_DURATION_SECONDS = int(MAX_DURATION_SECONDS)

if MAX_SIMULTANIOUS_REQUESTS:
    MAX_SIMULTANIOUS_REQUESTS = int(MAX_SIMULTANIOUS_REQUESTS)

if USER_RATE_LIMIT:
    USER_RATE_LIMIT = int(USER_RATE_LIMIT)

if USER_REQUEST_TIME:
    USER_REQUEST_TIME = int(USER_REQUEST_TIME)

# Define the maximum character limit for a single message
MAX_MESSAGE_LENGTH = os.getenv('MAX_MESSAGE_LENGTH')
if MAX_MESSAGE_LENGTH:
    MAX_MESSAGE_LENGTH = int(MAX_MESSAGE_LENGTH)
else:
    MAX_MESSAGE_LENGTH = 4096

# Create a semaphore lock to limit concurrent API requests
api_transcribe_semaphore = asyncio.Semaphore(1)
api_diarize_semaphore = asyncio.Semaphore(1)

processing_requests = asyncio.Queue()

# Set log format
if not LOG_FORMAT:
    LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"

formatter = logging.Formatter(LOG_FORMAT)

# Create a logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Set up logging to the console
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# Set up logging to a file
if LOG_FILENAME:
    file_handler = logging.FileHandler(LOG_FILENAME, encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
else:
    logger.warning("LOG_FILENAME not set! Logging to the file disabled!")

if API_URL_TRANSCRIBE:
    try:
        gradio_transcribe = Client(API_URL_TRANSCRIBE, hf_token=HF_TOKEN_TRANSCRIBE)
    except Exception as e:
        logger.error(f"API Transcribe Connect error: {str(e)}")
else:
    logger.warning("API_URL_TRANSCRIBE not set! Bot can't transribe audio!")

if API_URL_DIARIZE:
    try:
        gradio_diarize = Client(API_URL_DIARIZE, hf_token=HF_TOKEN_DIARIZE)
    except Exception as e:
        logger.error(f"API Diarize Connect error: {str(e)}")
else:
    logger.warning("API_URL_DIARIZE not set! Bot can't diarize audio!")

if not TELEGRAM_BOT_TOKEN:
    logger.error("TELEGRAM_BOT_TOKEN not set! App will crash soon...")

if not COMMAND_TRANSCRIBE:
    logger.warning("Bot transcribe command not set! Using default /text command!")
    COMMAND_TRANSCRIBE = "text"

if not COMMAND_DIARIZE:
    logger.warning("Bot diarize command not set! Using default /diarize command!")
    COMMAND_DIARIZE = "diarize"

bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()

request_count_semaphore = asyncio.Semaphore(1)
rate_limit_semaphore = asyncio.Semaphore(1)
request_delay_semaphore = asyncio.Semaphore(1)

# Global variable to keep track of simultaneous requests
global_request_count = 0

request_delay = 0

# Function to check the global request count
async def check_request_count():
    global global_request_count
    async with request_count_semaphore:
        return global_request_count

# Dictionary to store user request queues based on timestamps
user_request_queues = defaultdict(lambda: deque())

# Add supports to python 3.7-3.8 (asyncio.to_thread)
# Copied from source code: https://github.com/python/cpython/blob/main/Lib/asyncio/threads.py#L12
async def to_thread(func, /, *args, **kwargs):
    loop = asyncio.get_running_loop()
    ctx = contextvars.copy_context()
    func_call = partial(ctx.run, func, *args, **kwargs)
    return await loop.run_in_executor(None, func_call)


# Function to send a long message split into multiple parts
async def send_long_message(msg: types.Message, text: str):
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
                msg_next = await msg.edit_text(part)
            else:
                # Send subsequent parts as replies to the previous message
                msg_next = await msg_next.reply(part)
    except Exception as e:
        logger.error(f"Sending long message error: {str(e)}")
        if "msg_next" in locals():
            await msg_next.reply("Sending long message error!")
        else:
            await msg.reply("Sending long message error!")


# Function to perform the API request with retries
async def perform_api_request(data: bytes, id: str, msg: types.Message,
                                user_id: int, username: str, chat_id: int, diarize: bool):
    if diarize and not "gradio_diarize" in globals():
        logger.error(f"User ID: {user_id}, Chat ID: {chat_id}, Username: {username}, Diarize API is not connected!")
        await msg.edit_text("Diarize API is not connected!")
        return

    if not diarize and not "gradio_transcribe" in globals():
        logger.error(f"User ID: {user_id}, Chat ID: {chat_id}, Username: {username}, Transcribe API is not connected!")
        await msg.edit_text("Transcribe API is not connected!")
        return

    audio = {
        "name": id,
        "data": base64.b64encode(data).decode()
    }

    if diarize:
        try:
            async with api_diarize_semaphore:
                result = await to_thread(gradio_diarize.predict, audio, "transcribe", True, api_name="/predict")
                logger.info(f"User ID: {user_id}, Chat ID: {chat_id}, Username: {username}, File: {id}, Diarized: {result}")
        except Exception as e:
            logger.error(f"User ID: {user_id}, Chat ID: {chat_id}, Username: {username}, File: {id}, API Diarize Error: {str(e)}")
            await msg.edit_text("Diarize API error!")
            return
    else:
        try:
            async with api_transcribe_semaphore:
                result = await to_thread(gradio_transcribe.predict, audio, "transcribe", api_name="/predict")
                logger.info(f"User ID: {user_id}, Chat ID: {chat_id}, Username: {username}, File: {id}, Transcribed: {result}")
        except Exception as e:
            logger.error(f"User ID: {user_id}, Chat ID: {chat_id}, Username: {username}, File: {id}, API Transcribe Error: {str(e)}")
            await msg.edit_text("Transcribe API error!")
            return

    if len(result) <= MAX_MESSAGE_LENGTH:
        await msg.edit_text(result)
    elif result:
        await send_long_message(msg, result)
    else:
        await msg.edit_text("Text not recognized!")


# Function to check and enforce request limits
def request_limit():
    def decorator(func):
        @wraps(func)
        async def wrapper(*args):
            message = args[0]
            user = message.from_user
            user_id = user.id
            current_time = time.time()

            # Acquire the rate limit semaphore
            async with rate_limit_semaphore:
                if USER_RATE_LIMIT and USER_REQUEST_TIME:
                    # Get the user's request queue and remove old timestamps
                    user_queue = user_request_queues[user_id]
                    while user_queue and current_time - user_queue[0] > USER_REQUEST_TIME:
                        user_queue.popleft()

                    # Check if the user has exceeded the request limit
                    if len(user_queue) >= USER_RATE_LIMIT:
                        logger.info(f"User ID: {user_id}, Chat ID: {message.chat.id}, Username: {user.username}, Max request limit exceeded!")
                        return await message.reply("You have exceeded the request limit. Please try again later.")

                    # Add the current timestamp to the user's request queue
                    user_queue.append(current_time)

            return await func(*args)
        return wrapper
    return decorator


async def get_file(message: types.Message, reply: bool):
    user = message.from_user
    username = user.username
    user_id = user.id
    chat_id = message.chat.id

    # Check the global request count
    current_request_count = await check_request_count()
    if MAX_SIMULTANIOUS_REQUESTS and current_request_count >= MAX_SIMULTANIOUS_REQUESTS:
        logger.info(f"User ID: {user_id}, Chat ID: {chat_id}, Username: {username}, Reached max request limit!")
        await message.reply(f"Sorry, the maximum simultaneous request limit ({MAX_SIMULTANIOUS_REQUESTS}) has been reached. Please try again later.")
        return

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
                "\n", "-" * 30, "\n",
                "Send a voice, audio, video message or reply to it using commands!"
            )


# Function to process requests
@request_limit()
async def process_request(message: types.Message, reply=False, diarize=False):
    try:
        # Make 50ms delay for saving responce message order for multiple messages in a time
        global request_delay
        async with request_delay_semaphore:
            request_delay += 1
            delay = request_delay

        if delay:
            await asyncio.sleep(delay * 0.05)

        async with request_delay_semaphore:
            request_delay -= 1

        # Increment the global request count
        global global_request_count
        async with request_count_semaphore:
            global_request_count += 1

        result = await get_file(message, reply)
        if not result:
            return

        data, msg, fileid = result

        if diarize:
            await msg.edit_text("Diarizing...")
        else:
            await msg.edit_text("Transcribing...")

        user = message.from_user
        await perform_api_request(data, fileid, msg, user.id, user.username, message.chat.id, diarize)
    except Exception as e:
        logger.error(f"User ID: {user.id}, Chat ID: {message.chat.id}, Username: {user.username}, Processing error: {str(e)}")
    finally:
        async with request_count_semaphore:
            global_request_count -= 1


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


async def main():
    logger.info("App started!")
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"App Error: {str(e)}")


if __name__ == "__main__":
    asyncio.run(main())
