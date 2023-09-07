# Voice To Text Telegram Bot

This is a Telegram bot that provides speech recognition services using the Hugging Face API. You can send voice messages directly to the bot, or you can reply to a voice message with the `/text` command to receive a transcription of the message.

## Prerequisites

- A Telegram bot token: You can [create a bot on Telegram](https://core.telegram.org/bots#how-do-i-create-a-bot) and obtain the token.
- Hugging Face API read token: You'll need [an API token](https://huggingface.co/docs/hub/security-tokens) to use the Hugging Face speech recognition model.
- Python 3.7 or higher installed on your system.

## Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/yourusername/telegram-speech-recognition-bot.git
   cd telegram-speech-recognition-bot
   ```

2. Install the required Python packages:

    ```bash
    pip install -r requirements.txt
    ```

3. Replace "TELEGRAM_BOT_TOKEN", "HUGGING_FACE_API_TOKEN" and "API_URL" in the config.py file with your actual bot token, Hugging Face API token and url to preffered Hugging Face Model.

## Usage

1. Run the bot:

    ```bash
    python bot.py
    ```

2. Interact with the bot on Telegram: Send a voice message directly to the bot to receive a transcription. Reply to a voice message with `/text` to get a transcription.

## Logging

The bot logs user information, chat details, timestamps, and API results. Log messages are printed to the console and saved in a log file for reference.
