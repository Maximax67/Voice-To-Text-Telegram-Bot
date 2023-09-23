import base64
import asyncio
from gradio_client import Client
from aiogram import types

from logger import logger
from utils import to_thread, send_long_message
from request_limits import request_limit, make_request_delay, check_request_count, \
                            request_count_increment, request_count_decrement
from process_file import get_file
from config import API_URL_TRANSCRIBE, API_URL_DIARIZE, HF_TOKEN_TRANSCRIBE, HF_TOKEN_DIARIZE, \
                    MAX_MESSAGE_LENGTH, MAX_SIMULTANIOUS_REQUESTS


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


# Create a semaphore lock to limit concurrent API requests
api_transcribe_semaphore = asyncio.Semaphore(1)
api_diarize_semaphore = asyncio.Semaphore(1)

# Requests queues
transcribe_request_queue = asyncio.Queue()
diarize_request_queue = asyncio.Queue()


# Function to process requests
@request_limit()
async def process_request(message: types.Message, reply=False, diarize=False):
    try:
        # Check the global request count
        current_request_count = await check_request_count()
        if MAX_SIMULTANIOUS_REQUESTS and current_request_count > MAX_SIMULTANIOUS_REQUESTS - 1:
            user = message.from_user
            logger.info(f"User ID: {user.id}, Chat ID: {message.chat.id}, Username: {user.username}, Reached max request limit!")
            await message.reply(f"Sorry, the maximum simultaneous request limit has been reached: {MAX_SIMULTANIOUS_REQUESTS}. Please try again later.")
            return

        await request_count_increment()
        await make_request_delay()

        result = await get_file(message, reply)
        if not result:
            return

        data, msg, fileid = result

        user = message.from_user
        await perform_api_request(data, fileid, msg, user.id, user.username, message.chat.id, diarize)
    except Exception as e:
        logger.error(f"User ID: {user.id}, Chat ID: {message.chat.id}, Username: {user.username}, Processing error: {str(e)}")
    finally:
        await request_count_decrement()


# Fuction to process transcribe API queue
async def transcribe_queue_process():
    while True:
        async with api_transcribe_semaphore:
            # Get the message and its arguments from the queue
            audio, msg, user_id, chat_id, username = await transcribe_request_queue.get()
            await msg.edit_text("Transcribing...")

            try:
                result = await to_thread(gradio_transcribe.predict, audio, "transcribe", api_name="/predict")
                logger.info(f"User ID: {user_id}, Chat ID: {chat_id}, Username: {username}, File: {audio['name']}, Result: {result}")
            except Exception as e:
                logger.error(f"User ID: {user_id}, Chat ID: {chat_id}, Username: {username}, File: {audio['name']}, Transcribe API error: {str(e)}")
                await msg.edit_text("Transcribe API error!")
                continue

            try:
                if len(result) <= MAX_MESSAGE_LENGTH:
                    await msg.edit_text(result)
                elif result:
                    await send_long_message(msg, result, False)
                else:
                    await msg.edit_text("Text not recognized!")
            except Exception as e:
                logger.error(f"User ID: {user_id}, Chat ID: {chat_id}, Username: {username}, File: {audio['name']}, Error sending result: {str(e)}")
                await msg.edit_text("Error sending result!")


# Fuction to process diarize API queue
async def diarize_queue_process():
    while True:
        async with api_diarize_semaphore:
            # Get the message and its arguments from the queue
            audio, msg, user_id, chat_id, username = await diarize_request_queue.get()
            await msg.edit_text("Diarizing...")

            try:
                result = await to_thread(gradio_diarize.predict, audio, "transcribe", True, api_name="/predict")
                logger.info(f"User ID: {user_id}, Chat ID: {chat_id}, Username: {username}, File: {audio['name']}, Result: {result}")
            except Exception as e:
                logger.error(f"User ID: {user_id}, Chat ID: {chat_id}, Username: {username}, File: {audio['name']}, Diarize API error: {str(e)}")
                await msg.edit_text("Diarize API error!")
                continue

            try:
                if len(result) <= MAX_MESSAGE_LENGTH:
                    await msg.edit_text(result)
                elif result:
                    await send_long_message(msg, result, False)
                else:
                    await msg.edit_text("Text not recognized!")
            except Exception as e:
                logger.error(f"User ID: {user_id}, Chat ID: {chat_id}, Username: {username}, Error sending result: {str(e)}")
                await msg.edit_text("Error sending result!")


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
        if diarize_request_queue.qsize():
            await msg.edit_text("Queued! Please wait!")
        await diarize_request_queue.put((audio, msg, user_id, chat_id, username))
    else:
        if transcribe_request_queue.qsize():
            await msg.edit_text("Queued! Please wait!")
        await transcribe_request_queue.put((audio, msg, user_id, chat_id, username))

