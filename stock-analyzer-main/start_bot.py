"""
Start the Telegram bot with better error handling
"""
import logging
import sys
import os

# Setup comprehensive logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

try:
    from src.bot.telegram_bot import *
    from telegram.ext import ApplicationBuilder
    
    logger.info("="*80)
    logger.info("Starting Telegram Bot...")
    logger.info("="*80)
    
    if not TELEGRAM_BOT_TOKEN:
        logger.error("ERROR: TELEGRAM_BOT_TOKEN not found in config/env.")
        sys.exit(1)
    
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    
    start_handler = CommandHandler('start', start)
    analyze_handler = CommandHandler('analyze', analyze_command)
    stock_handler = CommandHandler('stock', analyze_command)
    
    # Text handler for direct symbols
    text_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message)
    
    application.add_handler(start_handler)
    application.add_handler(analyze_handler)
    application.add_handler(stock_handler)
    application.add_handler(text_handler)
    
    logger.info("Bot is polling... Press Ctrl+C to stop")
    logger.info("Check bot.log for detailed logs")
    application.run_polling()
    
except KeyboardInterrupt:
    logger.info("Bot stopped by user")
except Exception as e:
    logger.error(f"Fatal error: {e}", exc_info=True)
    sys.exit(1)

