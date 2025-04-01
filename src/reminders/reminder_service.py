from threading import Timer
from datetime import datetime
import logging
from typing import Dict

logger = logging.getLogger(__name__)


class ReminderService:
    def __init__(self, bot, storage):
        self.bot = bot
        self.storage = storage
        self.timers: Dict[str, Timer] = {}  # key: f"{task_id}_{option}", value: Timer

    def stop(self):
        for timer_key, timer in list(self.timers.items()):
            timer.cancel()
        self.timers.clear()
        logger.info("Reminder service stopped, all timers cancelled")

    def create_reminder(self, task_id, chat_id, deadline_str, reminder_delta, option_code):
        timer_key = f"{task_id}_{option_code}"

        try:
            deadline = datetime.strptime(deadline_str, "%d.%m.%Y %H:%M")
        except ValueError:
            logger.error(f"Invalid deadline format for task {task_id}")
            return False

        notify_time = deadline - reminder_delta
        delay = (notify_time - datetime.now()).total_seconds()
        if delay <= 0:
            logger.info(f"Reminder for task {task_id} ({option_code}) occurs in past")
            return False

        self.remove_reminder(task_id, option_code)

        timer = Timer(delay, self._notify, args=(task_id, chat_id))
        timer.start()
        self.timers[timer_key] = timer
        logger.info(f"Created reminder for task {task_id} with option {option_code}")
        return True

    def remove_reminder(self, task_id, option_code):
        timer_key = f"{task_id}_{option_code}"
        timer = self.timers.pop(timer_key, None)
        if timer:
            timer.cancel()
            logger.info(f"Removed reminder for task {task_id} with option {option_code}")
            return True
        return False

    def has_reminder(self, task_id, option_code):
        timer_key = f"{task_id}_{option_code}"
        return timer_key in self.timers

    def _notify(self, task_id, chat_id):
        try:
            task = self.storage.get_task(task_id)
            if not task:
                logger.error(f"Task {task_id} not found for notification")
                return

            project_id = task.get("project_id")
            project = self.storage.get_project(project_id)
            project_name = project.get("project_name", f"Проект {project_id[:8]}")

            message_text = f"📊 {project_name}:\n\n"
            message_text += f" {task.get('name', 'Задача без названия')}\n"
            message_text += f" Статус: {task.get('status', '—')}\n"
            message_text += f" Дедлайн: {task.get('deadline', '—')}\n\n"
            message_text += "⏰ Напоминание о скором дедлайне!"

            self.bot.send_message(chat_id, message_text)
            logger.info(f"Sent reminder notification for task {task_id}")
        except Exception as e:
            logger.error(f"Failed to send reminder notification for task {task_id}: {e}")
        finally:
            self.timers.pop(task_id, None)
