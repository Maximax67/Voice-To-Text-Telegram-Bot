# Replace with your bot token, model API URL, Hugging Face API token
TELEGRAM_BOT_TOKEN = ""
HUGGING_FACE_API_TOKEN = ""

# Example for UK language
API_URL = "https://api-inference.huggingface.co/models/arampacha/wav2vec2-xls-r-1b-uk"

HEADERS = {"Authorization": f"Bearer {HUGGING_FACE_API_TOKEN}"}

LOG_FILE_NAME = "bot.log"
LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"

# Waiting params for loading model on Hugging Face
RETRY_COUNT = 10
RETRY_DELAY = 15

# Maximum file size and duration limits (you can adjust these as needed)
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
MAX_DURATION_SECONDS = 120  # 2 minutes
