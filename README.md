# Voice To Text Telegram Bot

This is a Telegram bot that provides speech recognition services using the Hugging Face API. You can send voice messages directly to the bot, or you can reply to a voice message with the `/text` command (by default) to receive a transcription of the message.

## Prerequisites

- A Telegram bot token: You can [create a bot on Telegram](https://core.telegram.org/bots#how-do-i-create-a-bot) and obtain the token.
- Python 3.7 or higher installed on your system.

## Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/Maximax67/Voice-To-Text-Telegram-Bot
   cd Voice-To-Text-Telegram-Bot
   ```

2. Install the required Python packages:

    ```bash
    pip install -r requirements.txt
    ```

3. Create .env file and fill it according to .env.example. Paste your telegram bot token! You can adjust other params if you want.

## Usage

1. Run the bot:

    ```bash
    python bot.py
    ```

2. Interact with the bot on Telegram: Send a voice message directly to the bot to receive a transcription. Reply to a voice message with `/text` (by default) to get a transcription.

## Logging

The bot logs user information, chat details, timestamps, and API results. Log messages are printed to the console and saved in a log file for reference.
