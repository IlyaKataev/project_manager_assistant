START_MESSAGE = "Привет! Я бот для управления проектами. Используйте /help, чтобы узнать, что я умею делать."
HELP_MESSAGE = """Список доступных команд:
/start - приветственное сообщение
/help - показать список команд
/add_project - добавить новый проект
/projects - просмотреть список ваших проектов
/tasks - просмотреть ваши задачи"""

PROJECT_ADD_INSTRUCTION_MANAGER = """Для создания проекта выполните следующие шаги:

    1. Перейдите по ссылке, чтобы создать копию шаблона таблицы:
       https://docs.google.com/spreadsheets/d/1ul8Kg4IsujdldEYzlSnaJ6CPR7YONsV-vXybVf_aEQU/edit?usp=sharing

    2. Нажмите "Файл" -> "Создать копию"

    3. Откройте созданную копию и нажмите "Настройки доступа"

    4. Добавьте email бота как редактора:
       sheets-api-access-bot@project-manager-assistant.iam.gserviceaccount.com

    5. Скопируйте ссылку на вашу таблицу и отправьте ее мне"""

TASK_DETAILS_FORMAT = """📝 Задача: {task_name}
📌 Статус: {status}
👤 Исполнитель: {assignee}
⏰ Дедлайн: {deadline}
📝 Описание: {description}"""
