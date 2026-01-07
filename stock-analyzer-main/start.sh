#!/bin/bash

# Start the Telegram Bot in the background
echo "Starting Telegram Bot..."
python src/bot/telegram_bot.py &

# Start the Web Application in the foreground
echo "Starting Web Application..."
# Using exec to replace the shell process with the python process
exec python src/web/app.py
