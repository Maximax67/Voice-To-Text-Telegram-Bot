import os
import logging
import asyncio
import requests
import base64
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
from gradio_client import Client
from dotenv import load_dotenv

# Load .env variables
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
BOT_COMMAND = os.getenv('BOT_COMMAND')
API_URL = os.getenv('API_URL')
HF_TOKEN = os.getenv('HF_TOKEN')
LOG_FILENAME = os.getenv('LOG_FILENAME')
LOG_FORMAT = os.getenv('LOG_FORMAT')
MAX_FILE_SIZE = os.getenv('MAX_FILE_SIZE')
MAX_DURATION_SECONDS = os.getenv('MAX_DURATION_SECONDS')

if MAX_FILE_SIZE:
    MAX_FILE_SIZE = int(MAX_FILE_SIZE)

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

if not API_URL:
    logger.error("API_URL not set! Bot can't transribe audio!")
else:
    try:
        gradio_client = Client(API_URL, hf_token=HF_TOKEN)
    except Exception as e:
        logger.error(f"API Connect error: {str(e)}")

if not TELEGRAM_BOT_TOKEN:
    logger.error("TELEGRAM_BOT_TOKEN not set! App will crash soon...")

if not BOT_COMMAND:
    logger.warning("Bot command not set! Using default /text command!")
    BOT_COMMAND = "text"


# Function to perform the API request with retries
async def perform_api_request(data, id, msg, user_id, username, chat_id):
    async with api_request_lock:
        if not "gradio_client" in globals():
            logger.error(f"User ID: {user_id}, Chat ID: {chat_id}, Username: {username}, API is not connected!")
            await msg.edit_text("API is not connected!")
            return

        audio = {
            "name": id,
            "data": base64.b64encode(data).decode()
        }

        try:
            result = gradio_client.predict(
                audio,
                "transcribe",
                api_name="/predict"
            )
            logger.info(f"User ID: {user_id}, Chat ID: {chat_id}, Username: {username}, Response: {result}")
            await msg.edit_text(result)
        except Exception as e:
            logger.error(f"User ID: {user_id}, Chat ID: {chat_id}, Username: {username}, API Error: {str(e)}")
            await msg.edit_text("API error!")


# Function to download and process audio file
async def process_audio(update, context, message):
    user = update.effective_user
    username = user.username
    userid = user.id
    chat_id = update.effective_chat.id

    if message and (message.voice or message.audio):
        file = message.voice or message.audio

        # Check file size
        if MAX_FILE_SIZE and file.file_size > MAX_FILE_SIZE:
            logger.debug(f"User ID: {userid}, Chat ID: {chat_id}, Username: {username}, File exceeds size limit: {file.file_size}")
            await update.message.reply_text(f"File size exceeds the {MAX_FILE_SIZE / (1024 * 1024):.1f} MB limit. Please send a smaller file.")
            return

        # Check file duration for voice messages
        if MAX_DURATION_SECONDS and file.duration > MAX_DURATION_SECONDS:
            logger.debug(f"User ID: {userid}, Chat ID: {chat_id}, Username: {username}, Voice message duration exceeds limit: {file.duration} seconds")
            await update.message.reply_text(f"Voice message duration exceeds the {MAX_DURATION_SECONDS} seconds limit. Please send a shorter voice message.")
            return

        # Get file info
        file_info = await context.bot.get_file(file.file_id)
        file_path = file_info.file_path

        # Download the voice message
        try:
            response = requests.get(file_path)
            response.raise_for_status()  # Raise an exception for HTTP errors
        except requests.exceptions.MissingSchema as e:
            logger.error(f"User ID: {userid}, Chat ID: {chat_id}, Username: {username}, Invalid URL for file: {file.file_id}")
            await update.message.reply_text("Error downloading the file!")
            return
        except requests.exceptions.HTTPError as e:
            logger.error(f"User ID: {userid}, Chat ID: {chat_id}, Username: {username}, HTTP Error: {e.response.status_code}")
            await update.message.reply_text("HTTP error while downloading the file! Try again!")
            return
        except Exception as e:
            logger.error(f"User ID: {userid}, Chat ID: {chat_id}, Username: {username}, Error downloading: {file.file_id}, {str(e)}")
            await update.message.reply_text("Error downloading the file!")
            return

        if response.status_code == 200:
            logger.info(f"User ID: {userid}, Chat ID: {chat_id}, Username: {username}, Requested: {file.file_id}")
            msg = await update.message.reply_text("Transcribing...")

            asyncio.create_task(perform_api_request(response.content, file.file_id, msg, userid, username, chat_id))
        else:
            logger.error(f"User ID: {userid}, Chat ID: {chat_id}, Username: {username}, Error downloading: {file.file_id}, Status code: {response.status_code}")
            await update.message.reply_text("Error downloading the file!")
    else:
        logger.debug(f"User ID: {userid}, Chat ID: {chat_id}, Username: {username}, Invalid reply: {message}")
        await update.message.reply_text(f"Please reply to a voice message with /{BOT_COMMAND} to transcribe it.")


# Function to handle BOT_COMMAND command
async def bot_command(update: Update, context: CallbackContext):
    message = update.message.reply_to_message
    await process_audio(update, context, message)


# Function to handle direct voice messages
async def voice_message(update: Update, context: CallbackContext):
    message = update.message
    await process_audio(update, context, message)


# Function to handle non-voice messages in private chat
async def non_voice_message(update: Update):
    user = update.effective_user
    chat_id = update.effective_chat.id
    logger.debug(f"User ID: {user.id}, Chat ID: {chat_id}, Username: {user.username}, Received a non-voice message: {update.message.id}")
    await update.message.reply_text(f"Please send a voice message or use the /{BOT_COMMAND} command to transcribe it.")


def main():
    try:
        application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

        # Handle BOT_COMMAND command
        application.add_handler(CommandHandler(BOT_COMMAND, bot_command))

        # Handle direct voice or audio messages
        application.add_handler(MessageHandler(filters.ChatType.PRIVATE & (filters.VOICE | filters.AUDIO) & ~filters.COMMAND, voice_message))

        # Handle non-voice and non-audio messages in private chat
        application.add_handler(MessageHandler(filters.ChatType.PRIVATE & ~filters.VOICE & ~filters.AUDIO & ~filters.COMMAND, non_voice_message))

        logger.info("App started!")

        application.run_polling(allowed_updates=Update.ALL_TYPES)
    except Exception as e:
        logger.error(f"App Error: {str(e)}")


if __name__ == "__main__":
    main()