import threading
from datetime import datetime, timedelta

from src.reminders.reminder_service import ReminderService


def test_create_reminder(mock_bot, test_storage):
    task = {
        "task_id": "test-task-123",
        "name": "Test Task",
        "project_id": "test-project",
        "status": "В работе",
        "deadline": (datetime.now() + timedelta(days=1)).strftime("%d.%m.%Y %H:%M")
    }
    test_storage.save_task(task)

    project = {
        "project_id": "test-project",
        "project_name": "Test Project"
    }
    test_storage.add_project(project)

    reminder_service = ReminderService(mock_bot, test_storage)

    task_id = "test-task-123"
    chat_id = 12345
    deadline = task["deadline"]
    delta = timedelta(hours=1)
    option = "1h"

    result = reminder_service.create_reminder(task_id, chat_id, deadline, delta, option)
    assert result is True
    reminder_service.stop()


def test_delete_reminder(mock_bot, test_storage):
    task = {
        "task_id": "test-task-123",
        "name": "Test Task",
        "project_id": "test-project",
        "status": "В работе",
        "deadline": (datetime.now() + timedelta(days=1)).strftime("%d.%m.%Y %H:%M")
    }
    test_storage.save_task(task)

    project = {
        "project_id": "test-project",
        "project_name": "Test Project"
    }
    test_storage.add_project(project)

    reminder_service = ReminderService(mock_bot, test_storage)

    task_id = "test-task-123"
    chat_id = 12345
    deadline = task["deadline"]
    delta = timedelta(hours=1)
    option = "1h"

    reminder_service.create_reminder(task_id, chat_id, deadline, delta, option)
    timer_key = f"{task_id}_{option}"

    assert timer_key in reminder_service.timers

    result = reminder_service.remove_reminder(task_id, option)
    assert result is True

    assert timer_key not in reminder_service.timers

    result = reminder_service.remove_reminder(task_id, option)
    assert result is False


def test_reminder_after_deadline(mock_bot, test_storage):
    task = {
        "task_id": "test-task-123",
        "name": "Test Task",
        "project_id": "test-project",
        "status": "В работе",
        "deadline": (datetime.now() - timedelta(hours=2)).strftime("%d.%m.%Y %H:%M")
    }
    test_storage.save_task(task)

    reminder_service = ReminderService(mock_bot, test_storage)

    task_id = "test-task-123"
    chat_id = 12345
    deadline = task["deadline"]
    delta = timedelta(hours=1)
    option = "1h"

    result = reminder_service.create_reminder(task_id, chat_id, deadline, delta, option)
    assert result is False

    timer_key = f"{task_id}_{option}"
    assert timer_key not in reminder_service.timers
