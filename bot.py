import time
import json
import logging
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext

from config import TELEGRAM_BOT_TOKEN, API_URL, HEADERS, RETRY_COUNT, RETRY_DELAY

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)

def get_transcription(data):
    response = requests.post(API_URL, headers=HEADERS, data=data)
    if response.status_code == 200:
        result = json.loads(response.content.decode("utf-8"))
        transcription = result["text"]

        return response.status_code, transcription
    else:
        return response.status_code, "Error in speech recognition."

# Function to handle /text command
async def text_command(update: Update, context: CallbackContext):
    user = update.effective_user
    message = update.message.reply_to_message
    chat_id = update.effective_chat.id
    if message and message.voice:
        file_info = await context.bot.get_file(message.voice.file_id)
        file_path = file_info.file_path

        # Download the voice message
        response = requests.get(file_path)
        if response.status_code == 200:
            msg = await update.message.reply_text("Transcribing...")
            for i in range(RETRY_COUNT):
                code, result = get_transcription(response.content)
                if code == 503 and RETRY_COUNT:
                    if i == 0:
                        msg = await msg.edit_text("Loading model...")
                    time.sleep(RETRY_DELAY)
                    continue
                else:
                    break
            
            await msg.edit_text(result)

            # Log user and API information
            logger.info(f"User ID: {user.id}, Username: {user.username}, Name: {user.full_name}, Chat ID: {chat_id}, Timestamp: {update.message.date}, API Result: {result}")
        else:
            await update.message.reply_text("Error downloading voice message.")
    else:
        await update.message.reply_text("Please reply to a voice message with /text to transcribe it.")

# Function to handle direct voice messages
async def voice_message(update: Update, context: CallbackContext):
    user = update.effective_user
    chat_id = update.effective_chat.id
    file_info = await context.bot.get_file(update.message.voice.file_id)
    file_path = file_info.file_path

    response = requests.get(file_path)
    if response.status_code == 200:
        msg = await update.message.reply_text("Transcribing...")
        for i in range(RETRY_COUNT):
            code, result = get_transcription(response.content)
            if code == 503:
                if i == 0 and RETRY_COUNT:
                    msg = await msg.edit_text("Loading model...")
                time.sleep(RETRY_DELAY)
                continue
            else:
                break
        
        await msg.edit_text(result)

        # Log user and API information
        logger.info(f"User ID: {user.id}, Username: {user.username}, Name: {user.full_name}, Chat ID: {chat_id}, Timestamp: {update.message.date}, API Result: {result}")
    else:
        await update.message.reply_text("Error downloading voice message.")

def main():
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Handle /text command
    application.add_handler(CommandHandler("text", text_command))

    # Handle direct voice messages
    application.add_handler(MessageHandler(filters.ChatType.PRIVATE & filters.VOICE & ~filters.COMMAND, voice_message))

    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
