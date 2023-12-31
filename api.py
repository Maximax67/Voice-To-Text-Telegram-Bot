import base64
import asyncio
from gradio_client import Client
from aiogram import types

from logger import logger
from messages.log.api import *
from messages.telegram.api import *
from utils import to_thread, send_long_message
from request_limits import request_limit, make_request_delay, check_request_count, \
                            request_count_increment, request_count_decrement
from process_file import get_file
from utils import reply_message, edit_message
from config import API_URL_TRANSCRIBE, API_URL_DIARIZE, HF_TOKEN_TRANSCRIBE, HF_TOKEN_DIARIZE, \
                    MAX_MESSAGE_LENGTH, MAX_SIMULTANIOUS_REQUESTS


if API_URL_TRANSCRIBE:
    try:
        gradio_transcribe = Client(API_URL_TRANSCRIBE, hf_token=HF_TOKEN_TRANSCRIBE)
    except Exception as e:
        logger.error(API_TRANSSCRIBE_CONNECT_ERROR.format(str(e)))
else:
    logger.warning(API_URL_TRANSCRIBE_NOT_SET)

if API_URL_DIARIZE:
    try:
        gradio_diarize = Client(API_URL_DIARIZE, hf_token=HF_TOKEN_DIARIZE)
    except Exception as e:
        logger.error(API_DIARIZE_CONNECT_ERROR.format(str(e)))
else:
    logger.warning(API_URL_TRANSCRIBE_NOT_SET)


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
            logger.info(REQUEST_LIMIT_REACHED.format(user.id, message.chat.id, user.username))
            await reply_message(message, TG_REQUEST_LIMIT_REACHED.format(MAX_SIMULTANIOUS_REQUESTS))
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
        logger.error(PROCESSING_ERROR.format(user.id, message.chat.id, user.username, str(e)))
    finally:
        await request_count_decrement()


# Fuction to process transcribe API queue
async def transcribe_queue_process():
    while True:
        async with api_transcribe_semaphore:
            try:
                # Get the message and its arguments from the queue
                audio, msg, user_id, chat_id, username = await transcribe_request_queue.get()
                msg = await edit_message(msg, TG_WAIT_TRANSCRIBE)

                try:
                    result = await to_thread(gradio_transcribe.predict, audio, "transcribe", False, api_name="/predict")
                    result = result[0]
                    logger.info(TRANSCRIBE_RESULT.format(user_id, chat_id, username, audio['name'], result))
                except Exception as e:
                    logger.error(TRANSCRIBE_RESULT.format(user_id, chat_id, username, audio['name'], str(e)))
                    await edit_message(msg, TG_API_TRANSCRIBE_ERROR)
                    continue

                try:
                    if len(result) <= MAX_MESSAGE_LENGTH:
                        await edit_message(msg, result)
                    elif result:
                        await send_long_message(msg, result, False)
                    else:
                        await edit_message(msg, TG_API_NO_TEXT)
                except Exception as e:
                    logger.error(TRANSCRIBE_SENDING_ERROR.format(user_id, chat_id, username, audio['name'], str(e)))
                    await edit_message(msg, TG_API_TRANSCRIBE_SEND_ERROR)

                await asyncio.sleep(0.1)
            except Exception as e:
                continue


# Fuction to process diarize API queue
async def diarize_queue_process():
    while True:
        async with api_diarize_semaphore:
            try:
                # Get the message and its arguments from the queue
                audio, msg, user_id, chat_id, username = await diarize_request_queue.get()
                msg = await edit_message(msg, TG_WAIT_DIARIZE)

                try:
                    result = await to_thread(gradio_diarize.predict, audio, "transcribe", True, api_name="/predict")
                    logger.info(DIARIZE_RESULT.format(user_id, chat_id, username, audio['name'], result))
                except Exception as e:
                    if e:
                        logger.error(DIARIZE_ERROR.format(user_id, chat_id, username, audio['name'], str(e)))
                        await edit_message(msg, TG_API_DIARIZE_ERROR)
                    else:
                        logger.error(DIARIZE_NO_SPEAKERS_ERROR.format(user_id, chat_id, username, audio['name']))
                        await edit_message(msg, TG_API_DIARIZE_NO_SPEAKERS_ERROR)

                    continue

                try:
                    if len(result) <= MAX_MESSAGE_LENGTH:
                        await edit_message(msg, result)
                    elif result:
                        await send_long_message(msg, result, False)
                    else:
                        await edit_message(msg, TG_API_NO_TEXT)
                except Exception as e:
                    logger.error(DIARIZE_SENDING_ERROR.format(user_id, chat_id, username, audio['name'], str(e)))
                    await edit_message(msg, TG_API_DIARIZE_SEND_ERROR)

                await asyncio.sleep(0.1)
            except Exception as e:
                continue


# Function to perform the API request with retries
async def perform_api_request(data: bytes, id: str, msg: types.Message,
                                user_id: int, username: str, chat_id: int, diarize: bool):
    if diarize and not "gradio_diarize" in globals():
        logger.error(API_DIARIZE_NOT_CONNECTED.format(user_id, chat_id, username))
        await edit_message(msg, TG_API_DIARIZE_NOT_CONNECTED)
        return

    if not diarize and not "gradio_transcribe" in globals():
        logger.error(API_TRANSCRIBE_NOT_CONNECTED.format(user_id, chat_id, username))
        await edit_message(msg, TG_API_TRANSCRIBE_NOT_CONNECTED)
        return

    audio = {
        "name": id,
        "data": base64.b64encode(data).decode()
    }

    if diarize:
        if diarize_request_queue.qsize():
            msg = await edit_message(msg, TG_API_QUEUED)
        await diarize_request_queue.put((audio, msg, user_id, chat_id, username))
    else:
        if transcribe_request_queue.qsize():
            msg = await edit_message(msg, TG_API_QUEUED)
        await transcribe_request_queue.put((audio, msg, user_id, chat_id, username))
