# Replace with your bot token, model API URL, Hugging Face API token
TELEGRAM_BOT_TOKEN = ""

# Default Huggingface space
API_URL = "https://sanchit-gandhi-whisper-large-v2.hf.space/"

# Only for private workspaces, leave empty
HF_TOKEN = ""

LOG_FILE_NAME = "bot.log"
LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"

# Maximum file size and duration limits (you can adjust these as needed, may be limited by default API)
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
MAX_DURATION_SECONDS = 120  # 2 minutes
