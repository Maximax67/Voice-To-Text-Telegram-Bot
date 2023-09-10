import os
import logging
import asyncio
import base64
from pydub import AudioSegment
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

SUPPORTED_FILE_EXTENSIONS = ('mid', 'mp3', 'opus', 'oga', 'ogg', 'wav', 'webm', 'weba', 'flac',
                        'wma', 'aiff', 'opus', 'm4a', 'au', 'mp4', 'avi', 'mkv', 'mov')

if MAX_FILE_SIZE:
    MAX_FILE_SIZE = float(MAX_FILE_SIZE) * 1024 * 1024

if MAX_DURATION_SECONDS:
    MAX_DURATION_SECONDS = int(MAX_DURATION_SECONDS)

# Create a threading lock to ensure safe access to shared resources
api_request_lock = asyncio.Lock()

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

if not API_URL_TRANSCRIBE:
    logger.warning("API_URL_TRANSCRIBE not set! Bot can't transribe audio!")
else:
    try:
        gradio_transcribe = Client(API_URL_TRANSCRIBE, hf_token=HF_TOKEN_TRANSCRIBE)
    except Exception as e:
        logger.error(f"API Transcribe Connect error: {str(e)}")

if not API_URL_DIARIZE:
    logger.warning("API_URL_DIARIZE not set! Bot can't diarize audio!")
else:
    try:
        gradio_diarize = Client(API_URL_DIARIZE, hf_token=HF_TOKEN_DIARIZE)
    except Exception as e:
        logger.error(f"API Diarize Connect error: {str(e)}")

if not TELEGRAM_BOT_TOKEN:
    logger.error("TELEGRAM_BOT_TOKEN not set! App will crash soon...")

if not COMMAND_TRANSCRIBE:
    logger.warning("Bot transcribe command not set! Using default /text command!")
    COMMAND_TRANSCRIBE = "text"

if not COMMAND_DIARIZE:
    logger.warning("Bot diarize command not set! Using default /diarize command!")
    COMMAND_TRANSCRIBE = "diarize"

bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()

# Function to perform the API request with retries
async def perform_api_request(data, id, msg, user_id, username, chat_id, diarize=False):
    async with api_request_lock:
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
                result = await asyncio.to_thread(gradio_diarize.predict, audio, "transcribe", True, api_name="/predict")
                logger.info(f"User ID: {user_id}, Chat ID: {chat_id}, Username: {username}, Diarized: {result}")
                await msg.edit_text(result)
            except Exception as e:
                logger.error(f"User ID: {user_id}, Chat ID: {chat_id}, Username: {username}, API Diarize Error: {str(e)}")
                await msg.edit_text("Diarize API error!")
        else:
            try:
                result = await asyncio.to_thread(gradio_transcribe.predict, audio, "transcribe", api_name="/predict")
                logger.info(f"User ID: {user_id}, Chat ID: {chat_id}, Username: {username}, Transcribed: {result}")
                await msg.edit_text(result)
            except Exception as e:
                logger.error(f"User ID: {user_id}, Chat ID: {chat_id}, Username: {username}, API Transcribe Error: {str(e)}")
                await msg.edit_text("Transcribe API error!")

# Function to download and process audio file
async def process_file(message: types.Message, reply, diarize):
    user = message.from_user
    username = user.username
    user_id = user.id
    chat_id = message.chat.id

    trigger_msg = message
    if reply:
        message = message.reply_to_message

    if message:
        file = message.voice or message.audio or message.video_note or message.video or message.document
    else:
        file = None

    if file:
        logger.info(f"User ID: {user_id}, Chat ID: {chat_id}, Username: {username}, Requested: {file.file_id}")

        # Check file size
        if MAX_FILE_SIZE and file.file_size > MAX_FILE_SIZE:
            logger.info(f"User ID: {user_id}, Chat ID: {chat_id}, Username: {username}, File exceeds size the limit")
            await message.reply(f"File size exceeds the {MAX_FILE_SIZE / (1024 * 1024):.1f} MB limit! Please send a smaller file.")
            return

        # Check file duration for voice messages
        if hasattr(file, "duration") and MAX_DURATION_SECONDS and file.duration > MAX_DURATION_SECONDS:
            logger.info(f"User ID: {user_id}, Chat ID: {chat_id}, Username: {username}, Duration exceeds the limit")
            await message.reply(f"Duration exceeds the {MAX_DURATION_SECONDS} seconds limit! Please send a shorter version!")
            return

        # Request file path
        try:
            file_id = file.file_id
            file_requested = await bot.get_file(file_id)
            file_path = file_requested.file_path

            # Double-Check file size
            if MAX_FILE_SIZE and file_requested.file_size > MAX_FILE_SIZE:
                logger.info(f"User ID: {user_id}, Chat ID: {chat_id}, Username: {username}, File exceeds size the limit")
                await message.reply(f"File size exceeds the {MAX_FILE_SIZE / (1024 * 1024):.1f} MB limit! Please send a smaller file.")
                return
        except Exception as e:
            logger.error(f"User ID: {user_id}, Chat ID: {chat_id}, Username: {username}, Can't request file: {file.file_id}, {str(e)}")
            await message.reply("Error requesting file data!")
            return

        # Check file extension
        last_dot_index = file_path.rfind('.')
        if last_dot_index == -1:
            logger.info(f"User ID: {user_id}, Chat ID: {chat_id}, Username: {username}, Unknown file extension")
            await message.reply("Unknown file extension!")
            return

        file_extension = file_path[last_dot_index + 1:].lower()
        if not file_extension in SUPPORTED_FILE_EXTENSIONS:
            logger.info(f"User ID: {user_id}, Chat ID: {chat_id}, Username: {username}, Unsupported file format: {file_extension}")
            await message.reply(f"Unsupported file format: {file_extension}")
            return

        msg = await message.reply("Downloading file...")

        # Download the voice message
        try:
            file_content = await bot.download_file(file_path)
        except Exception as e:
            logger.error(f"User ID: {user_id}, Chat ID: {chat_id}, Username: {username}, Error downloading: {file.file_id}, {str(e)}")
            await msg.edit_text("Error downloading the file!")
            return

        await msg.edit_text("Extracting audio...")
        try:
            audio_segment = AudioSegment.from_file(file_content)
            duration = len(audio_segment) / 1000.0 # Convert milliseconds to seconds

            # Check file duration for audio messages
            if MAX_DURATION_SECONDS and duration > MAX_DURATION_SECONDS:
                logger.info(f"User ID: {user_id}, Chat ID: {chat_id}, Username: {username}, Duration exceeds the limit")
                await msg.edit_text(f"Duration exceeds the {MAX_DURATION_SECONDS} seconds limit! Please send a shorter version!")
                return

            audio_content = audio_segment.export(format="wav").read()
        except Exception as e:
            logger.error(f"User ID: {user_id}, Chat ID: {chat_id}, Username: {username}, Extracting audio error: {file.file_id}, {str(e)}")
            await msg.edit_text("Error extracting audio!")
            return

        if diarize:
            await msg.edit_text("Diarizing...")
        else:
            await msg.edit_text("Transcribing...")

        # Make api request
        await perform_api_request(audio_content, file.file_id, msg, user_id, username, chat_id, diarize)
    elif diarize:
        logger.info(f"User ID: {user_id}, Chat ID: {chat_id}, Username: {username}, Invalid diarize message: {trigger_msg.message_id}")
        await trigger_msg.reply(f"Please reply to a voice / audio / video message with /{COMMAND_DIARIZE} to diarize it.")
    else:
        logger.info(f"User ID: {user_id}, Chat ID: {chat_id}, Username: {username}, Invalid transcribe message: {trigger_msg.message_id}")
        await trigger_msg.reply(f"Please reply to a voice / audio / video message with /{COMMAND_TRANSCRIBE} to transcribe it.")


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
                "\n\nSupported files: ",
                Bold(', '.join(SUPPORTED_FILE_EXTENSIONS)),
                "\n", "-" * 30, "\n",
                "Send a voice / audio / video message or reply to it using commands!"
            )


# Help function
@dp.message(Command("help"))
async def transcribe_command(message: types.Message):
    user = message.from_user
    username = user.username
    user_id = user.id
    chat_id = message.chat.id
    logger.info(f"User ID: {user_id}, Chat ID: {chat_id}, Username: {username}, Used help command")
    await message.reply(**get_bot_settings().as_kwargs())


# Function to handle COMMAND_TRANSCRIBE
@dp.message(Command(COMMAND_TRANSCRIBE))
async def transcribe_command(message: types.Message):
    asyncio.create_task(process_file(message, True, False))


# Function to handle COMMAND_DIARIZE
@dp.message(Command(COMMAND_DIARIZE))
async def diarize_command(message: types.Message):
    asyncio.create_task(process_file(message, True, True))


# Function to handle direct voice messages
@dp.message()
async def voice_message(message: types.Message):
    if message.content_type in {'voice', 'audio', 'video_note', 'video', 'document'}:
        if message.chat.type == 'private' or INSTANT_REPLY_IN_GROUPS:
            asyncio.create_task(process_file(message, False, False))
    elif message.chat.type == 'private':
        user = message.from_user
        username = user.username
        user_id = user.id
        chat_id = message.chat.id
        logger.info(f"User ID: {user_id}, Chat ID: {chat_id}, Username: {username}, Sended invalid message: {message.message_id}")
        await message.reply(f"Send a voice / audio / video message or reply to it using commands! (see /help).")


async def main():
    logger.info("App started!")
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"App Error: {str(e)}")


if __name__ == "__main__":
    asyncio.run(main())
