import telebot
import logging

from src.utils.helpers import validate_username, extract_spreadsheet_id, ensure_user_data
from src.utils.messages import PROJECT_ADD_INSTRUCTION_MANAGER

logger = logging.getLogger(__name__)


def register_project_handlers(bot, storage, gsheets):
    @bot.message_handler(commands=['add_project'])
    def add_project(message):
        logger.info(f"User {message.from_user.id} is adding a project")
        markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
        markup.add('Руководитель проекта', 'Участник проекта')
        bot.send_message(message.chat.id, "Вы руководитель или участник проекта?", reply_markup=markup)
        bot.register_next_step_handler(message, process_user_role)

    def process_user_role(message):
        user_id = message.from_user.id
        selected_role = message.text

        logger.info(f"User {user_id} selected role: {selected_role}")

        if selected_role == 'Руководитель проекта':
            bot.send_message(message.chat.id, PROJECT_ADD_INSTRUCTION_MANAGER,
                             reply_markup=telebot.types.ReplyKeyboardRemove())
            bot.register_next_step_handler(message, process_manager_spreadsheet)

        elif selected_role == 'Участник проекта':
            bot.send_message(message.chat.id, "Введите ID проекта, предоставленный руководителем:",
                             reply_markup=telebot.types.ReplyKeyboardRemove())
            bot.register_next_step_handler(message, process_member_project_id)

        else:
            logger.warning(f"User {user_id} provided invalid role: {selected_role}")
            bot.send_message(message.chat.id, "Пожалуйста, выберите один из предложенных вариантов.")
            bot.register_next_step_handler(message, process_user_role)

    def process_manager_spreadsheet(message):
        user_id = message.from_user.id
        username = message.from_user.username

        wait_msg = bot.send_message(message.chat.id, "Идет создание проекта, пожалуйста, подождите...")

        spreadsheet_link = message.text
        logger.info(f"Processing manager spreadsheet from user {user_id}: {spreadsheet_link}")

        try:
            spreadsheet_id = extract_spreadsheet_id(spreadsheet_link)
            if not spreadsheet_id:
                raise ValueError("Не удалось извлечь ID таблицы из ссылки")

            existing_project = storage.get_project(spreadsheet_id)
            if existing_project:
                if existing_project.get("created_by") != user_id:
                    bot.edit_message_text(chat_id=message.chat.id,
                                          message_id=wait_msg.message_id,
                                          text="Проект с таким ID уже существует. Если вы не являетесь его руководителем, пожалуйста, присоединитесь к проекту как участник.")
                    return
                else:
                    bot.edit_message_text(chat_id=message.chat.id,
                                          message_id=wait_msg.message_id,
                                          text="Вы уже создали этот проект.")
                    return

            logger.info(f"Extracted spreadsheet ID: {spreadsheet_id}")

            try:
                sheet = gsheets.gc.open_by_key(spreadsheet_id)
                if not sheet:
                    raise ValueError("Не удалось открыть таблицу по ID")
                project_name = sheet.title
                logger.info(f"Got project name '{project_name}' for spreadsheet {spreadsheet_id}")
            except Exception as e:
                project_name = f"Проект {spreadsheet_id[:8]}"
                logger.warning(f"Failed to get project name for {spreadsheet_id}: {str(e)}")

            sheet_data = gsheets.get_sheet_data(spreadsheet_id, "Лист1")
            if sheet_data is None:
                logger.warning(f"Failed to access spreadsheet {spreadsheet_id} for user {user_id}")
                bot.edit_message_text(chat_id=message.chat.id,
                                      message_id=wait_msg.message_id,
                                      text="Не удалось получить доступ к таблице. Убедитесь, что вы правильно добавили бота как редактора и отправьте ссылку еще раз.")
                bot.register_next_step_handler(message, process_manager_spreadsheet)
                return

            project_data = {
                "project_id": spreadsheet_id,
                "google_sheets_id": spreadsheet_id,
                "project_name": project_name,
                "sheet_name": "Лист1",
                "created_by": user_id
            }
            storage.add_project(project_data)

            ensure_user_data(storage, user_id, username)

            if storage.add_user_to_project(user_id, spreadsheet_id, "manager", username):
                logger.info(f"Successfully added user {user_id} as manager to project {spreadsheet_id}")

                bot_username = bot.get_me().username
                invite_link = f"https://t.me/{bot_username}?start=project_{spreadsheet_id}"

                bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=wait_msg.message_id,
                    text=(f"Проект \"{project_name}\" успешно создан!\n\n"
                          f"Отправьте участникам эту ссылку для присоединения к проекту:\n{invite_link}\n\n"
                          f"Или ID проекта:\n{spreadsheet_id}")
                )
            else:
                logger.info(f"User {user_id} already added to project {spreadsheet_id}")
                bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=wait_msg.message_id,
                    text="Этот проект уже добавлен."
                )

        except Exception as e:
            logger.error(f"Error adding project for user {user_id}: {str(e)}", exc_info=True)
            bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=wait_msg.message_id,
                text=(f"Ошибка добавления проекта: {str(e)}\n\n"
                      "Пожалуйста, отправьте корректную ссылку на Google Таблицу.")
            )
            bot.register_next_step_handler(message, process_manager_spreadsheet)

    def process_member_project_id(message):
        user_id = message.from_user.id
        username = message.from_user.username
        project_id = message.text.strip()

        logger.info(f"Processing member project ID from user {user_id}: {project_id}")

        try:
            project = storage.get_project(project_id)
            if not project:
                logger.warning(f"Project {project_id} not found in storage for user {user_id}")
                bot.send_message(message.chat.id,
                                 "Проект не найден. Убедитесь, что ID проекта верный.")
                return

            sheet_data = gsheets.get_sheet_data(project_id, "Лист1")
            if sheet_data is None:
                logger.warning(f"Failed to access project {project_id} sheet for user {user_id}")
                bot.send_message(message.chat.id,
                                 "Не удалось получить доступ к проекту. Убедитесь, что ID проекта верный и руководитель добавил бота как редактора.")
                return

            if storage.add_user_to_project(user_id, project_id, "member", username):
                logger.info(f"Successfully added user {user_id} as member to project {project_id}")
                project_name = project.get("project_name", f"Проект {project_id[:8]}")
                bot.send_message(message.chat.id, f"Вы успешно добавлены в проект \"{project_name}\"!")
            else:
                logger.info(f"User {user_id} already added to project {project_id}")
                project_name = project.get("project_name", f"Проект {project_id[:8]}")
                bot.send_message(message.chat.id, f"Вы уже добавлены в проект \"{project_name}\".")

        except Exception as e:
            logger.error(f"Error adding user {user_id} to project: {str(e)}", exc_info=True)
            bot.send_message(message.chat.id, f"Ошибка добавления в проект: {str(e)}")

    @bot.message_handler(func=lambda message: message.text and message.text.startswith('/start project_'))
    def join_project_via_link(message):
        user_id = message.from_user.id
        username = message.from_user.username

        if not validate_username(bot, message.chat.id, username):
            return

        try:
            project_id = message.text.split('_', 1)[1].strip()
            logger.info(f"User {user_id} is joining project {project_id} via deep link")

            project = storage.get_project(project_id)
            if not project:
                bot.send_message(message.chat.id, "Проект не найден. Проверьте ссылку.")
                return

            ensure_user_data(storage, user_id, username)

            if storage.add_user_to_project(user_id, project_id, "member", username):
                project_name = project.get("project_name", f"Проект {project_id[:8]}")
                bot.send_message(message.chat.id, f"Вы успешно добавлены в проект \"{project_name}\"!")
            else:
                project_name = project.get("project_name", f"Проект {project_id[:8]}")
                bot.send_message(message.chat.id, f"Вы уже участвуете в проекте \"{project_name}\".")

        except Exception as e:
            logger.error(f"Error processing deep link: {str(e)}", exc_info=True)
            bot.send_message(message.chat.id, "Некорректная ссылка для присоединения к проекту.")

    @bot.message_handler(commands=['projects'])
    def list_projects(message):
        user_id = message.from_user.id
        username = message.from_user.username
        if not validate_username(bot, message.chat.id, username):
            return

        projects = storage.get_user_projects(user_id)
        if not projects:
            bot.send_message(
                message.chat.id,
                "У вас нет добавленных проектов. Используйте /add_project для добавления."
            )
            return

        if len(projects) > 1:
            markup = telebot.types.InlineKeyboardMarkup(row_width=1)
            for proj in projects:
                name = proj.get("project_name", proj["project_id"][:8])
                short_id = proj["project_id"][:8]
                role = "👑" if proj.get("role") == "manager" else "👤"
                markup.add(telebot.types.InlineKeyboardButton(
                    f"{role} {name}",
                    callback_data=f"projects_sel_{short_id}"
                ))
            bot.send_message(
                message.chat.id,
                "Выберите проект:",
                reply_markup=markup
            )
        else:
            show_project_menu(message.chat.id, projects[0])

    @bot.callback_query_handler(func=lambda call: call.data.startswith('projects_sel_'))
    def project_select_callback(call):
        user_id = call.from_user.id
        short_id = call.data.split('_', 2)[2]
        projects = storage.get_user_projects(user_id)
        project = next((p for p in projects if p["project_id"].startswith(short_id)), None)
        if not project:
            bot.answer_callback_query(call.id, "Проект не найден")
            return

        show_project_menu(call.message.chat.id, project, call.message.message_id)
        bot.answer_callback_query(call.id)

    def show_project_menu(chat_id, project, message_id=None):
        name = project.get("project_name", project["project_id"][:8])
        role = "Руководитель" if project.get("role") == "manager" else "Участник"
        text = f"📂 {name}\nРоль: {role}\nID: {project['project_id']}"

        short_id = project["project_id"][:8]
        markup = telebot.types.InlineKeyboardMarkup(row_width=1)
        markup.add(telebot.types.InlineKeyboardButton(
            "📊 Список задач",
            callback_data=f"tasks_{short_id}"
        ))
        markup.add(telebot.types.InlineKeyboardButton(
            "⬅️ Назад к проектам",
            callback_data="projects_back"
        ))

        if message_id:
            bot.edit_message_text(
                text, chat_id, message_id, reply_markup=markup
            )
        else:
            bot.send_message(
                chat_id, text, reply_markup=markup
            )

    @bot.callback_query_handler(func=lambda call: call.data == 'projects_back')
    def projects_back_callback(call):
        user_id = call.from_user.id
        chat_id = call.message.chat.id
        message_id = call.message.message_id

        projects = storage.get_user_projects(user_id)
        if not projects:
            bot.edit_message_text(
                "У вас нет добавленных проектов. Используйте /add_project для добавления.",
                chat_id, message_id
            )
            return

        markup = telebot.types.InlineKeyboardMarkup(row_width=1)
        for proj in projects:
            name = proj.get("project_name", proj["project_id"][:8])
            short_id = proj["project_id"][:8]
            role = "👑" if proj.get("role") == "manager" else "👤"
            markup.add(telebot.types.InlineKeyboardButton(
                f"{role} {name}",
                callback_data=f"projects_sel_{short_id}"
            ))

        bot.edit_message_text(
            "Выберите проект:",
            chat_id, message_id, reply_markup=markup
        )
        bot.answer_callback_query(call.id)
