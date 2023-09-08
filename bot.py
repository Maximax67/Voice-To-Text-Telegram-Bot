import logging
import asyncio
import requests
import base64
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
from gradio_client import Client

from config import TELEGRAM_BOT_TOKEN, API_URL, HF_TOKEN, LOG_FILE_NAME, LOG_FORMAT, MAX_FILE_SIZE, MAX_DURATION_SECONDS

# Create a threading lock to ensure safe access to shared resources
api_request_lock = asyncio.Lock()

formatter = logging.Formatter(LOG_FORMAT)

# Set up logging to a file
file_handler = logging.FileHandler(LOG_FILE_NAME, encoding='utf-8')
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(formatter)

# Set up logging to the console
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(formatter)

# Create a logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(file_handler)
logger.addHandler(console_handler)

# Load API
gradio_client = Client(API_URL, hf_token=HF_TOKEN)

# Function to perform the API request with retries
async def perform_api_request(data, id, msg, user_id, username, chat_id):
    async with api_request_lock:
        audio = {
            "name": id,
            "data": base64.b64encode(data).decode()
        }
        result = gradio_client.predict(
				audio,
				"transcribe",
				api_name="/predict"
        )

        logger.info(f"User ID: {user_id}, Chat ID: {chat_id}, Username: {username}, Response: {result}")
        await msg.edit_text(result)

# Function to download and process audio file
async def process_audio(update, context, message):
    user = update.effective_user
    username = user.username
    userid = user.id
    chat_id = update.effective_chat.id

    if message and (message.voice or message.audio):
        file = message.voice or message.audio

        # Check file size
        if file.file_size > MAX_FILE_SIZE:
            logger.debug(f"User ID: {userid}, Chat ID: {chat_id}, Username: {username}, File exceeds size limit: {file.file_size}")
            await update.message.reply_text(f"File size exceeds the {MAX_FILE_SIZE / (1024 * 1024):.1f} MB limit. Please send a smaller file.")
            return

        # Check file duration for voice messages
        if file.duration > MAX_DURATION_SECONDS:
            logger.debug(f"User ID: {userid}, Chat ID: {chat_id}, Username: {username}, Voice message duration exceeds limit: {file.duration} seconds")
            await update.message.reply_text(f"Voice message duration exceeds the {MAX_DURATION_SECONDS} seconds limit. Please send a shorter voice message.")
            return

        file_info = await context.bot.get_file(file.file_id)
        file_path = file_info.file_path

        # Download the voice message
        response = requests.get(file_path)
        if response.status_code == 200:
            logger.info(f"User ID: {userid}, Chat ID: {chat_id}, Username: {username}, Requested: {file.file_id}")
            msg = await update.message.reply_text("Transcribing...")

            asyncio.create_task(perform_api_request(response.content, file.file_id, msg, userid, username, chat_id))
        else:
            logger.info(f"User ID: {userid}, Chat ID: {chat_id}, Username: {username}, Error downloading voice: {file.file_id}")
            await update.message.reply_text("Error downloading voice message.")
    else:
        logger.debug(f"User ID: {userid}, Chat ID: {chat_id}, Username: {username}, Invalid reply: {message}")
        await update.message.reply_text("Please reply to a voice message with /text to transcribe it.")


# Function to handle /text command
async def text_command(update: Update, context: CallbackContext):
    message = update.message.reply_to_message
    await process_audio(update, context, message)


# Function to handle direct voice messages
async def voice_message(update: Update, context: CallbackContext):
    message = update.message
    await process_audio(update, context, message)


# Function to handle non-voice messages in private chat
async def non_voice_message(update: Update, context: CallbackContext):
    user = update.effective_user
    chat_id = update.effective_chat.id
    logger.debug(f"User ID: {user.id}, Chat ID: {chat_id}, Username: {user.username}, Received a non-voice message")
    await update.message.reply_text("Please send a voice message or use the /text command to transcribe it.")


def main():
    logger.info("App started")

    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Handle /text command
    application.add_handler(CommandHandler("text", text_command))

    # Handle direct voice or audio messages
    application.add_handler(MessageHandler(filters.ChatType.PRIVATE & (filters.VOICE | filters.AUDIO) & ~filters.COMMAND, voice_message))

    # Handle non-voice and non-audio messages in private chat
    application.add_handler(MessageHandler(filters.ChatType.PRIVATE & ~filters.VOICE & ~filters.AUDIO & ~filters.COMMAND, non_voice_message))

    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
