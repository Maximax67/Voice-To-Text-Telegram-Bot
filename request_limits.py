import time
import asyncio
from functools import wraps
from collections import defaultdict, deque

from logger import logger
from messages.log.other import REQUEST_LIMIT
from messages.telegram.other import TG_RATE_LIMIT_EXCEEDED
from config import USER_RATE_LIMIT, USER_REQUEST_TIME

rate_limit_semaphore = asyncio.Semaphore(1)
request_count_semaphore = asyncio.Semaphore(1)
request_delay_semaphore = asyncio.Semaphore(1)

# Dictionary to store user request queues based on timestamps
user_request_queues = defaultdict(lambda: deque())

# Global variable to keep track of simultaneous requests
global_request_count = 0

# Variable to make delay for replying to messages in order
request_delay = 0


# Function to check the global request count
async def check_request_count():
    async with request_count_semaphore:
        global global_request_count
        return global_request_count


# Make 150ms delay for saving responce message order for multiple messages in a time
async def make_request_delay():
    global request_delay
    async with request_delay_semaphore:
        request_delay += 1
        delay = request_delay

    if delay:
        await asyncio.sleep(delay * 0.15)

    async with request_delay_semaphore:
        request_delay -= 1


# Increment the global request count
async def request_count_increment():
    async with request_count_semaphore:
        global global_request_count
        global_request_count += 1


# Decrement the global request count
async def request_count_decrement():
    async with request_count_semaphore:
        global global_request_count
        global_request_count -= 1


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
                        logger.info(REQUEST_LIMIT.format(user_id, message.chat.id, user.username))
                        return await message.reply(TG_RATE_LIMIT_EXCEEDED)

                    # Add the current timestamp to the user's request queue
                    user_queue.append(current_time)

            return await func(*args)
        return wrapper
    return decorator
