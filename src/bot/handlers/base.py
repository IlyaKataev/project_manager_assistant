import logging

from src.utils.messages import START_MESSAGE, HELP_MESSAGE

logger = logging.getLogger(__name__)


def register_base_handlers(bot):
    @bot.message_handler(commands=['start'])
    def start_message(message):
        logger.info(f"User {message.from_user.id} started the bot")
        bot.send_message(message.chat.id, START_MESSAGE)

    @bot.message_handler(commands=['help'])
    def help_message(message):
        logger.info(f"User {message.from_user.id} requested help")
        bot.send_message(message.chat.id, HELP_MESSAGE)

    @bot.message_handler(func=lambda message: message.text)
    def handle_unknown_command(message):
        logger.info(f"Unknown command from user {message.from_user.id}: {message.text}")
        bot.send_message(message.chat.id, "Неизвестная команда. Используйте /help, чтобы показать список команд.")
