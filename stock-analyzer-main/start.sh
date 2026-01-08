#!/bin/bash
# Start the Telegram Bot in the background
python -m src.bot.telegram_bot &

# Start the Flask Web App (Foreground)
# Gunicorn will bind to $PORT provided by Render
gunicorn src.web.app:app
