import logging
from telebot import types
from datetime import datetime

from src.utils.helpers import validate_username, shorten_task_id, find_task_by_short_id
from src.utils.messages import TASK_DETAILS_FORMAT

logger = logging.getLogger(__name__)


def register_task_handlers(bot, storage, gsheets):
    @bot.message_handler(commands=['tasks'])
    def list_tasks(message):
        user_id = message.from_user.id
        username = message.from_user.username
        logger.info(f"User {user_id} requested task list")

        if not validate_username(bot, message.chat.id, username):
            return

        user_projects = storage.get_user_projects(user_id)
        if not user_projects:
            logger.info(f"No projects found for user {user_id}")
            bot.send_message(message.chat.id,
                             "У вас нет добавленных проектов. Используйте /add_project для добавления.")
            return

        if len(user_projects) > 1:
            markup = types.InlineKeyboardMarkup(row_width=1)
            for project in user_projects:
                project_name = project.get("project_name", f"Проект {project['project_id'][:8]}")
                short_id = project['project_id'][:8]
                markup.add(types.InlineKeyboardButton(
                    text=project_name,
                    callback_data=f"tasks_{short_id}"
                ))
            bot.send_message(message.chat.id, "Выберите проект для просмотра задач:", reply_markup=markup)
        else:
            project = user_projects[0]
            show_project_tasks(message.chat.id, project, user_id, bot, storage)

    @bot.callback_query_handler(func=lambda call: call.data.startswith('tasks_'))
    def project_tasks_callback(call):
        short_project_id = call.data.split('_')[1]
        user_id = call.from_user.id

        user_projects = storage.get_user_projects(user_id)
        selected_project = None

        for project in user_projects:
            if project['project_id'].startswith(short_project_id):
                selected_project = project
                break

        if selected_project:
            chat_id = call.message.chat.id
            message_id = call.message.message_id
            bot.edit_message_text(
                "Загружаю задачи...",
                chat_id,
                message_id
            )
            show_project_tasks(chat_id, selected_project, user_id, bot, storage, message_id)
        else:
            bot.answer_callback_query(call.id, "Проект не найден в вашем списке")

    def show_task_details(chat_id, task, message_id=None):
        task_details = TASK_DETAILS_FORMAT.format(
            task_name=task.get("name", "Без названия"),
            status=task.get("status", "Не указан"),
            assignee=f"{task.get('assignee_name', '')} {task.get('assignee', '')}".strip(),
            deadline=task.get("deadline", "Не указан"),
            description=task.get("description", "Нет описания")
        )

        markup = types.InlineKeyboardMarkup(row_width=2)
        short_task_id = shorten_task_id(task["task_id"])
        status_buttons = {
            "Выдана": ["➡️ Взять в работу", "w"],
            "В работе": ["➡️ Отправить на проверку", "c"],
            "На проверке": ["⬅️ Вернуть в работу", "w"],
            "Завершена": ["🔄 Переоткрыть", "r"]
        }
        current_status = task.get("status")
        if current_status in status_buttons:
            button_text, status_code = status_buttons[current_status]
            markup.add(types.InlineKeyboardButton(button_text, callback_data=f"st_{short_task_id}_{status_code}"))

        markup.add(types.InlineKeyboardButton("Оставить обратную связь", callback_data=f"fb_{short_task_id}"))
        markup.add(types.InlineKeyboardButton("Управление напоминаниями", callback_data=f"rm.menu_{short_task_id}"))

        if message_id:
            bot.edit_message_text(
                task_details,
                chat_id,
                message_id,
                reply_markup=markup
            )
        else:
            bot.send_message(chat_id, task_details, reply_markup=markup)

    @bot.callback_query_handler(func=lambda call: call.data.startswith('task_'))
    def task_details_callback(call):
        short_id = call.data.split('_')[1]
        task = find_task_by_short_id(short_id, storage)
        if not task:
            bot.answer_callback_query(call.id, "Задача не найдена")
            return
        show_task_details(call.message.chat.id, task, call.message.message_id)

    @bot.callback_query_handler(func=lambda call: call.data.startswith('page_'))
    def page_navigation_callback(call):
        parts = call.data.split('_')
        if len(parts) != 3:
            bot.answer_callback_query(call.id, "Неверный формат данных")
            return

        short_project_id = parts[1]
        try:
            page = int(parts[2])
        except ValueError:
            bot.answer_callback_query(call.id, "Неверный формат страницы")
            return

        user_id = call.from_user.id
        user_projects = storage.get_user_projects(user_id)

        selected_project = None
        for project in user_projects:
            if project['project_id'].startswith(short_project_id):
                selected_project = project
                break

        if selected_project:
            show_project_tasks(call.message.chat.id, selected_project, user_id, bot, storage,
                               call.message.message_id, page=page)
            bot.answer_callback_query(call.id)
        else:
            bot.answer_callback_query(call.id, "Проект не найден")

    @bot.callback_query_handler(func=lambda call: call.data.startswith('st_'))
    def change_task_status(call):
        parts = call.data.split('_')
        short_id = parts[1]
        status_code = parts[2]

        new_status_map = {"w": "В работе", "c": "На проверке", "r": "В работе", "d": "Выдана"}
        new_status = new_status_map.get(status_code)
        if not new_status:
            bot.answer_callback_query(call.id, "Некорректный статус")
            return

        task = None
        for tid, task_data in storage.get_all_tasks().items():
            if shorten_task_id(tid) == short_id:
                task = task_data
                task["task_id"] = tid
                break
        if not task:
            bot.answer_callback_query(call.id, "Задача не найдена")
            return

        try:
            project_id = task.get("project_id")
            project = storage.get_project(project_id)
            sheet_name = project.get("sheet_name", "Лист1")

            sheet_data = gsheets.get_sheet_data(project_id, sheet_name)
            headers = sheet_data[0]
            task_id_col = headers.index("ID задачи") if "ID задачи" in headers else None
            status_col = headers.index("Статус") if "Статус" in headers else None

            task_row = None
            for row_idx, row in enumerate(sheet_data[1:], 2):
                if row[task_id_col] == task["task_id"]:
                    task_row = row_idx
                    break

            gsheets.update_cell(project_id, sheet_name, task_row, status_col + 1, new_status)
            task["status"] = new_status
            task["last_updated"] = datetime.now().isoformat()
            storage.save_task(task)

            bot.answer_callback_query(call.id, f"Статус изменен на '{new_status}'")
            show_task_details(call.message.chat.id, task, call.message.message_id)

        except Exception as e:
            logger.error(f"Error updating task status: {str(e)}")
            bot.answer_callback_query(call.id, "Не удалось обновить статус задачи")

    @bot.callback_query_handler(func=lambda call: call.data.startswith('fb_'))
    def feedback_handler(call):
        logger.info(f"Handling feedback request for user {call.from_user.id}")
        short_id = call.data.split('_')[1]

        task = find_task_by_short_id(short_id, storage)
        if not task:
            logger.warning(f"Task with short_id {short_id} not found")
            bot.answer_callback_query(call.id, "Задача не найдена")
            return

        task_id = task["task_id"]
        task_name = task.get("name", "Задача без названия")

        if not hasattr(bot, 'feedback_states'):
            bot.feedback_states = {}

        bot.feedback_states[call.from_user.id] = task_id
        logger.info(f"Set feedback state for user {call.from_user.id}, task_id: {task_id}")

        bot.answer_callback_query(call.id)
        bot.send_message(
            call.message.chat.id,
            f"Введите обратную связь по задаче \"{task_name}\" (до 200 символов):"
        )
        bot.register_next_step_handler(call.message, process_feedback)

    def process_feedback(message):
        user_id = message.from_user.id
        logger.info(f"Processing feedback from user {user_id}")

        if not hasattr(bot, 'feedback_states') or user_id not in bot.feedback_states:
            logger.warning(f"Feedback session expired for user {user_id}")
            bot.send_message(message.chat.id, "Ошибка: сессия обратной связи истекла. Попробуйте снова.")
            return

        task_id = bot.feedback_states[user_id]
        feedback_text = message.text.strip()

        if len(feedback_text) > 200:
            logger.info(f"Feedback text too long ({len(feedback_text)} chars) from user {user_id}")
            bot.send_message(
                message.chat.id,
                "Ваш комментарий превышает 200 символов. Пожалуйста, сократите текст."
            )
            bot.register_next_step_handler(message, process_feedback)
            return

        wait_msg = bot.send_message(message.chat.id, "Обратная связь сохраняется...")

        try:
            task = storage.get_task(task_id)
            if not task:
                logger.error(f"Task {task_id} not found in storage")
                bot.edit_message_text("Ошибка: задача не найдена.", message.chat.id, wait_msg.message_id)
                del bot.feedback_states[user_id]
                return

            project_id = task.get("project_id")
            project = storage.get_project(project_id)
            sheet_name = project.get("sheet_name", "Лист1")

            sheet_data = gsheets.get_sheet_data(project_id, sheet_name)
            if not sheet_data:
                logger.error(f"Could not get sheet data for project {project_id}")
                bot.edit_message_text("Ошибка: не удалось получить данные таблицы.",
                                      message.chat.id, wait_msg.message_id)
                return

            headers = sheet_data[0]

            try:
                task_id_col = headers.index("ID задачи")
                feedback_col = headers.index("Обратная связь")
            except ValueError as e:
                logger.error(f"Required column not found: {str(e)}")
                bot.edit_message_text("Ошибка: необходимые столбцы не найдены в таблице.",
                                      message.chat.id, wait_msg.message_id)
                return

            task_row = None
            for row_idx, row in enumerate(sheet_data[1:], 2):
                if len(row) > task_id_col and row[task_id_col] == task_id:
                    task_row = row_idx
                    break

            if not task_row:
                logger.error(f"Task row not found for task_id {task_id}")
                bot.edit_message_text("Ошибка: строка задачи не найдена в таблице.",
                                      message.chat.id, wait_msg.message_id)
                return

            gsheets.update_cell(
                project_id,
                sheet_name,
                task_row,
                feedback_col + 1,
                feedback_text
            )
            logger.info(f"Updated feedback in sheet for task {task_id}")

            task["feedback"] = feedback_text
            task["last_updated"] = datetime.now().isoformat()
            storage.save_task(task)
            logger.info(f"Saved feedback to storage for task {task_id}")

            bot.edit_message_text("Спасибо! Ваша обратная связь сохранена.",
                                  message.chat.id, wait_msg.message_id)
            del bot.feedback_states[user_id]

        except Exception as e:
            logger.error(f"Error saving feedback: {str(e)}", exc_info=True)
            bot.edit_message_text("Не удалось сохранить обратную связь. Попробуйте позже.",
                                  message.chat.id, wait_msg.message_id)


def show_project_tasks(chat_id, project, user_id, bot, storage, edit_message_id=None, page=1):
    project_id = project["project_id"]
    project_name = project.get("project_name", f"Проект {project_id[:8]}")

    user_tasks = storage.get_user_tasks(user_id, project_id)

    if not user_tasks:
        response_text = f"У вас нет назначенных задач в проекте \"{project_name}\"."
        if edit_message_id:
            bot.edit_message_text(response_text, chat_id, edit_message_id)
        else:
            bot.send_message(chat_id, response_text)
        return

    page_size = 10
    total_tasks = len(user_tasks)
    total_pages = (total_tasks + page_size - 1) // page_size
    page = max(1, min(page, total_pages))
    start_idx = (page - 1) * page_size
    end_idx = min(start_idx + page_size, total_tasks)

    current_page_tasks = user_tasks[start_idx:end_idx]

    response = f"📊 {project_name} (стр. {page}/{total_pages}):\n\n"

    markup = types.InlineKeyboardMarkup(row_width=1)

    for i, task in enumerate(current_page_tasks, start=start_idx + 1):
        task_name = task.get("name", f"Задача {i}")
        status = task.get("status", "—")
        deadline = task.get("deadline", "—")

        response += f"{i:>2}. {task_name}\n"
        response += f"    Статус: {status}\n"
        response += f"    Дедлайн: {deadline}\n\n"

        short_id = shorten_task_id(task['task_id'])

        markup.add(types.InlineKeyboardButton(
            f"{i}. {task_name[:30]}{'...' if len(task_name) > 30 else ''}",
            callback_data=f"task_{short_id}"
        ))

    nav_buttons = []
    short_pid = project_id[:8]
    if page > 1:
        nav_buttons.append(types.InlineKeyboardButton("« Назад", callback_data=f"page_{short_pid}_{page - 1}"))
    if page < total_pages:
        nav_buttons.append(types.InlineKeyboardButton("Вперед »", callback_data=f"page_{short_pid}_{page + 1}"))

    if nav_buttons:
        markup.row(*nav_buttons)

    if edit_message_id:
        bot.edit_message_text(response, chat_id, edit_message_id, reply_markup=markup)
    else:
        bot.send_message(chat_id, response, reply_markup=markup)

