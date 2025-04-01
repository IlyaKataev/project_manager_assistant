import logging
from telebot import types
from datetime import datetime, timedelta
from src.utils.helpers import find_task_by_short_id
from telebot.apihelper import ApiTelegramException

logger = logging.getLogger(__name__)

REMINDER_OPTIONS = [
    ("1 минута", "1m"),
    ("1 час", "1h"),
    ("24 часа", "24h"),
    ("7 дней", "7d")
]


def register_reminder_handlers(bot, storage):
    def build_reminder_markup(short_task_id, task_id, reminder_service):
        markup = types.InlineKeyboardMarkup(row_width=2)

        for label, code in REMINDER_OPTIONS:
            is_active = reminder_service.has_reminder(task_id, code)
            button_text = f"🔔 {label}" if is_active else f"🔕 {label}"
            callback_data = f"rm.set_{short_task_id}_{code}"
            markup.add(types.InlineKeyboardButton(button_text, callback_data=callback_data))

        markup.add(types.InlineKeyboardButton("⬅️ Назад", callback_data=f"task_{short_task_id}"))

        return markup

    @bot.callback_query_handler(func=lambda call: call.data.startswith('rm.menu_'))
    def reminder_callback(call):
        short_task_id = call.data.split('_')[1]
        task = find_task_by_short_id(short_task_id, storage)
        if not task:
            bot.answer_callback_query(call.id, "Задача не найдена.")
            return

        chat_id = call.message.chat.id
        message_id = call.message.message_id
        task_id = task["task_id"]
        reminder_service = bot.reminder_service

        markup = build_reminder_markup(short_task_id, task_id, reminder_service)
        try:
            bot.edit_message_text("⏰ Управление напоминаниями:", chat_id, message_id, reply_markup=markup)
        except ApiTelegramException as e:
            if "message is not modified" in str(e):
                pass
            else:
                raise
        bot.answer_callback_query(call.id)

    @bot.callback_query_handler(func=lambda call: call.data.startswith('rm.set_'))
    def set_reminder_callback(call):
        parts = call.data.split('_')
        if len(parts) < 3:
            bot.answer_callback_query(call.id, "Неверные данные напоминания.")
            return

        short_task_id = parts[1]
        option = parts[2]
        task = find_task_by_short_id(short_task_id, storage)
        if not task:
            bot.answer_callback_query(call.id, "Задача не найдена.")
            return

        task_id = task["task_id"]
        chat_id = call.message.chat.id
        reminder_service = bot.reminder_service

        reminder_deltas = {
            "1m": timedelta(minutes=1),
            "1h": timedelta(hours=1),
            "24h": timedelta(hours=24),
            "7d": timedelta(days=7)
        }
        delta_texts = {"1m": "1 минуту", "1h": "1 час", "24h": "24 часа", "7d": "7 дней"}
        delta = reminder_deltas.get(option)
        if not delta:
            bot.answer_callback_query(call.id, "Неверное время.")
            return

        deadline = task.get("deadline")
        if not deadline:
            bot.answer_callback_query(call.id, "У задачи нет дедлайна.")
            return

        if reminder_service.has_reminder(task_id, option):
            reminder_service.remove_reminder(task_id, option)
            bot.answer_callback_query(call.id, f"Напоминание за {delta_texts.get(option)} отключено")
        else:
            try:
                deadline_dt = datetime.strptime(deadline, "%d.%m.%Y %H:%M")
                notify_time = deadline_dt - delta
                if notify_time <= datetime.now():
                    bot.answer_callback_query(call.id, "Напоминание невозможно: время уже прошло")
                else:
                    success = reminder_service.create_reminder(task_id, chat_id, deadline, delta, option)
                    if success:
                        bot.answer_callback_query(call.id, f"Установлено напоминание за {delta_texts.get(option)}")
                    else:
                        bot.answer_callback_query(call.id, "Не удалось установить напоминание")
            except ValueError:
                bot.answer_callback_query(call.id, "Неверный формат дедлайна")

        markup = build_reminder_markup(short_task_id, task_id, reminder_service)
        try:
            bot.edit_message_text("⏰ Управление напоминаниями:", chat_id, call.message.message_id, reply_markup=markup)
        except ApiTelegramException as e:
            if "message is not modified" in str(e):
                pass
            else:
                raise
