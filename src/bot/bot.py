import telebot
import os
import logging
from dotenv import load_dotenv

from src.bot.handlers.base import register_base_handlers
from src.bot.handlers.project import register_project_handlers
from src.bot.handlers.task import register_task_handlers
from src.bot.handlers.reminder import register_reminder_handlers

logger = logging.getLogger(__name__)

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")


def setup_bot_handlers(storage, gsheets):
    bot = telebot.TeleBot(BOT_TOKEN)

    register_project_handlers(bot, storage, gsheets)
    register_task_handlers(bot, storage, gsheets)
    register_reminder_handlers(bot, storage)
    register_base_handlers(bot)

    return bot


def start_bot_polling(bot):
    logger.info("Start bot polling")
    try:
        bot.polling(none_stop=True)
    except Exception as e:
        logger.error(f"Error in polling: {str(e)}")
        raise
