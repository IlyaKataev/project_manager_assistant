import hashlib


def extract_spreadsheet_id(spreadsheet_link):
    try:
        return spreadsheet_link.split('/d/')[1].split('/')[0]
    except Exception:
        return None


def validate_username(bot, chat_id, username):
    if not username:
        bot.send_message(chat_id,
                         "Для работы с проектами нужен username в Telegram. Пожалуйста, задайте его в настройках.")
        return False
    return True


def ensure_user_data(storage, user_id, username):
    user_data = storage.get_user_data(user_id)
    if not user_data:
        user_data = {
            "user_id": user_id,
            "username": username,
            "projects": []
        }
        storage.save_user_data(user_data)
        return

    if username != user_data["username"]:
        user_data["username"] = username
        storage.save_user_data(user_data)
        return user_data, True

    return user_data, False

# Используется префикс, размер callback data не более 64 байт
def shorten_task_id(task_id):
    hash_obj = hashlib.md5(task_id.encode())
    return hash_obj.hexdigest()[:8]


def find_task_by_short_id(short_id, storage):
    all_tasks = storage.get_all_tasks()
    for task_id, task_data in all_tasks.items():
        if shorten_task_id(task_id) == short_id:
            task = task_data.copy()
            task["task_id"] = task_id
            return task
    return None
