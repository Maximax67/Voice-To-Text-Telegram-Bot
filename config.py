# Replace with your bot token, model API URL, Hugging Face API token
TELEGRAM_BOT_TOKEN = ""
HUGGING_FACE_API_TOKEN = ""

# Example for UK language
API_URL = "https://api-inference.huggingface.co/models/arampacha/wav2vec2-xls-r-1b-uk"

HEADERS = {"Authorization": f"Bearer {HUGGING_FACE_API_TOKEN}"}

# Waiting params for loading model on Hugging Face
RETRY_COUNT = 10
RETRY_DELAY = 15
