import logging
from src.bot.bot import start_bot_polling, setup_bot_handlers
from src.utils.storage import Storage
from src.gsheets.client import GSheetsClient
from src.gsheets.sync_service import GSheetsSyncService
from src.reminders.reminder_service import ReminderService

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler()
    ],
)
logger = logging.getLogger(__name__)

if __name__ == '__main__':
    try:
        storage = Storage()
        gsheets = GSheetsClient()

        sync_service = GSheetsSyncService(storage, gsheets)
        sync_service.start()

        bot = setup_bot_handlers(storage, gsheets)
        bot.sync_service = sync_service

        reminder_service = ReminderService(bot, storage)
        bot.reminder_service = reminder_service

        try:
            start_bot_polling(bot)
        finally:
            bot.sync_service.stop()
            bot.reminder_service.stop()

    except Exception as e:
        logger.critical(f"Fatal error: {str(e)}", exc_info=True)
