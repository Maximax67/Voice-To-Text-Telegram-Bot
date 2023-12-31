# Voice To Text Telegram Bot

[![License](https://img.shields.io/github/license/Maximax67/Voice-To-Text-Telegram-Bot)](https://github.com/Maximax67/Voice-To-Text-Telegram-Bot/blob/main/LICENSE)
[![Telegram Bot](https://img.shields.io/badge/Telegram-Voice%20To%20Text%20Bot-blue.svg?logo=telegram)](https://t.me/maximax_voice_bot)

This is a Telegram bot that provides speech recognition services using the Gradio API space. You can send voice, audio, video, video-noted directly to the bot, or you can reply to the message with the `/text` command (by default) to receive a transcription of it. Also you can get speaker diarization using `/diarize` command (by default).

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

2. Interact with the bot on Telegram: Send the message directly to the bot to receive a transcription. Reply to the message with `/text` (by default) to get a transcription or with `/diarize` (by default) to get speaker diarization of it.

## Customization

You can set your own commands for transcribing and diarization, max file size and duration. Also you can enable "instant reply in groups" option that allow bot to trigger to every voice, video, audio messages and get transcription of it. You can configuire logs params.

## Protection

You can set up requests limits for users and for simultaneous API requests. It will protect you from DDOS attacks and voice messages spamming.

## Admin commands

To set admin users' or chat IDs, update the .env file. These users are authorized to execute admin commands, including:
* `/logsfile` to retrieve the entire log file.
* `/logs N` to retrieve the last `N` lines of the log file.
* `/file file_id` to access files requested by users. The file ID is displayed in the logs.
* `/broadcast id1,id2,id3 message` to broadcast the `message` to all users `id` and chats `id` separated by comma. If some message was replied with that command, it will be forwarded to all selected users and chats. Specify `message` in that case is not necessary.
* `/adminbroadcast message` to broadcast the `message` to all admins and admin chats. If some message was replied with that command, it will be forwarded to all admins. Specify `message` in that case is not necessary.
* `/chatid` to get chat id where the command was sent.
* `/disable` to make bot available only for admins.
* `/enable` to make bot available for everyone (default state on startup).

## Logging

The bot logs user timestamps, information, chat details, usernames, API requests and results. Log messages are printed to the console and saved in a log file for reference.

You can set your own log format in .env file. Also you can change logging templates by changing values in files in messages/telegram folder.
