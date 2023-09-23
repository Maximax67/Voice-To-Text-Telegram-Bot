import os
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

ADMIN_ID = os.getenv('ADMIN_ID')

LOG_FILENAME = os.getenv('LOG_FILENAME')
LOG_FORMAT = os.getenv('LOG_FORMAT')

MAX_FILE_SIZE = os.getenv('MAX_FILE_SIZE')
MAX_DURATION_SECONDS = os.getenv('MAX_DURATION_SECONDS')

MAX_SIMULTANIOUS_REQUESTS = os.getenv('MAX_SIMULTANIOUS_REQUESTS')

USER_RATE_LIMIT = os.getenv('USER_RATE_LIMIT')
USER_REQUEST_TIME = os.getenv('USER_REQUEST_TIME')

# Define the maximum character limit for a single message
MAX_MESSAGE_LENGTH = os.getenv('MAX_MESSAGE_LENGTH')

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

if ADMIN_ID:
    ADMIN_ID = [int(x) for x in ADMIN_ID.split(",")]

if MAX_MESSAGE_LENGTH:
    MAX_MESSAGE_LENGTH = int(MAX_MESSAGE_LENGTH)
else:
    MAX_MESSAGE_LENGTH = 4096

# Set log format
if not LOG_FORMAT:
    LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"
