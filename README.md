# Voice To Text Telegram Bot

[![License](https://img.shields.io/github/license/Maximax67/Voice-To-Text-Telegram-Bot)](https://github.com/Maximax67/Voice-To-Text-Telegram-Bot/blob/main/LICENSE)

This is a Telegram bot that provides speech recognition services using the Gradio API space. You can send voice messages directly to the bot, or you can reply to a voice message with the `/text` command (by default) to receive a transcription of the message.

## Prerequisites

- Telegram Bot Token: Create your own Telegram bot and obtain a unique token from [Telegram's BotFather](https://core.telegram.org/bots#how-do-i-create-a-bot).
- Python 3.7 or Higher: Ensure that you have Python 3.7 or a higher version installed on your system to run the bot.

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
