import logging
import re
from threading import Thread, Event
import uuid
from datetime import datetime
import time

logger = logging.getLogger(__name__)


class GSheetsSyncService:
    def __init__(self, storage, gsheets, sync_interval=10):
        self.storage = storage
        self.gsheets = gsheets
        self.sync_interval = sync_interval
        self.stop_event = Event()
        self.sync_thread = None

        self.COLUMN_NAME = {
            "name": "Название",
            "description": "Описание",
            "assignee_name": "ФИО исполнителя",
            "assignee": "ТГ исполнителя",
            "deadline": "Дедлайн",
            "status": "Статус",
            "feedback": "Обратная связь",
            "task_id": "ID задачи"
        }

        self.TASK_VALID_STATUSES = ["Выдана", "В работе", "На проверке", "Завершена"]

    def start(self):
        if self.sync_thread is None or not self.sync_thread.is_alive():
            self.stop_event.clear()
            self.sync_thread = Thread(target=self._sync_loop)
            self.sync_thread.daemon = True
            self.sync_thread.start()
            logger.info("Sheet sync service started")

    def stop(self):
        if self.sync_thread and self.sync_thread.is_alive():
            self.stop_event.set()
            self.sync_thread.join(timeout=5)
            logger.info("Sheet sync service stopped")

    def _sync_loop(self):
        while not self.stop_event.is_set():
            try:
                projects = self.storage.get_all_projects()
                for project_id, project in projects.items():
                    try:
                        self.sync_project(project_id)
                    except Exception as e:
                        logger.error(f"Error syncing project {project_id}: {str(e)}", exc_info=True)
                    finally:
                        time.sleep(2.5)
            except Exception as e:
                logger.error(f"Error in sync loop: {str(e)}", exc_info=True)

            self.stop_event.wait(self.sync_interval)

    def sync_project(self, project_id):
        project = self.storage.get_project(project_id)
        if not project:
            logger.warning(f"Project {project_id} not found in storage")
            return

        # Получаем данные из Google Sheets
        sheet_name = project.get("sheet_name", "Лист1")
        sheet_data = self.gsheets.get_sheet_data(project_id, sheet_name)
        if not sheet_data:
            logger.warning(f"Could not get sheet data for project {project_id}")
            return

        # Если пустая, то хотя бы создаем заголовки
        if len(sheet_data) == 0:
            headers = [self.COLUMN_NAME[key] for key in ["name", "description", "assignee_name",
                                                         "assignee", "deadline", "status", "feedback", "task_id"]]
            self.gsheets.update_sheet_data(project_id, sheet_name, [headers])
            logger.info(f"Created header row for project {project_id}")
            return

        headers = sheet_data[0]
        if all(not cell.strip() for cell in headers if isinstance(cell, str)):
            headers = [self.COLUMN_NAME[key] for key in ["name", "description", "assignee_name",
                                                         "assignee", "deadline", "status", "feedback", "task_id"]]
        # logger.info(f"Sheet headers: {headers}")

        column_indices = {}
        for key, name in self.COLUMN_NAME.items():
            try:
                column_indices[key] = headers.index(name)
            except ValueError:
                column_indices[key] = None
        if column_indices.get("task_id") is None:
            headers.append(self.COLUMN_NAME["task_id"])
            column_indices["task_id"] = len(headers) - 1

        data_rows = sheet_data[1:] if len(sheet_data) > 1 else []
        processed_sheet_data = [headers]
        empty_rows_count = 0

        existing_tasks = self.storage.get_project_tasks(project_id)
        existing_task_ids = set(existing_tasks.keys())
        processed_task_ids = set()

        for row in data_rows:
            if all(not str(cell).strip() for cell in row):
                empty_rows_count += 1
                continue

            # Расширяем строку, если нужно
            while len(row) < len(headers):
                row.append("")

            # logger.info(f"Processing row: {row}")

            # Получаем task_id или генерируем новый
            task_id = None
            idx = column_indices.get("task_id")
            if idx is not None and idx < len(row):
                task_id = row[idx]
            if not task_id:
                task_id = str(uuid.uuid4())[:30]
                row[idx] = task_id

            task = {
                "task_id": task_id,
                "project_id": project_id,
                "name": "",
                "description": "",
                "assignee_name": "",
                "assignee": "",
                "deadline": "",
                "status": self.TASK_VALID_STATUSES[0],
                "feedback": "",
                "last_updated": datetime.now().isoformat()
            }

            # Заполняем поля задачи из данных строки (статус и дедлайн)
            for field, idx in column_indices.items():
                if idx is not None and idx < len(row):
                    if field == "status":
                        status_value = row[idx]
                        if status_value not in self.TASK_VALID_STATUSES:
                            task[field] = self.TASK_VALID_STATUSES[0]
                            row[idx] = self.TASK_VALID_STATUSES[0]
                        else:
                            task[field] = status_value
                    elif field == "deadline":
                        deadline_value = str(row[idx]).strip()

                        # дд.мм.гггг чч:мм
                        full_pattern = re.fullmatch(r"\d{2}\.\d{2}\.\d{4}\s+\d{2}:\d{2}", deadline_value)
                        # дд.мм.гггг
                        date_pattern = re.fullmatch(r"\d{2}\.\d{2}\.\d{4}", deadline_value)

                        try:
                            if date_pattern:
                                date_obj = datetime.strptime(deadline_value, "%d.%m.%Y")
                                formatted_date = date_obj.strftime("%d.%m.%Y") + " 23:59"
                                task["deadline"] = formatted_date
                                row[idx] = formatted_date
                            elif full_pattern:
                                datetime.strptime(deadline_value, "%d.%m.%Y %H:%M")
                                task["deadline"] = deadline_value
                            else:
                                task[field] = row[idx] = ""
                        except ValueError:
                            task[field] = row[idx] = ""
                    else:
                        task[field] = row[idx]

            # assignee_idx = column_indices.get("assignee")
            # if assignee_idx is not None and assignee_idx < len(row):
            #     logger.info(f"Assignee value from sheet: '{row[assignee_idx]}'")

            if task["assignee"] and not task["assignee"].startswith("@"):
                task["assignee"] = "@" + task["assignee"].strip()
                assignee_idx = column_indices.get("assignee")
                if assignee_idx is not None:
                    row[assignee_idx] = task["assignee"]

            self.storage.save_task(task)
            processed_task_ids.add(task_id)
            processed_sheet_data.append(row)

        # Удаляем задачи, которые были удалены из таблицы
        deleted_tasks = existing_task_ids - processed_task_ids
        for t_id in deleted_tasks:
            self.storage.delete_task(t_id)
            logger.info(f"Deleted task {t_id} as it's no longer in the spreadsheet")

        for _ in range(empty_rows_count):
            processed_sheet_data.append([""] * len(headers))

        # Наконец-то обновляем данные в таблице
        self.gsheets.update_sheet_data(project_id, sheet_name, processed_sheet_data)
        logger.info(
            f"Updated spreadsheet with {len(processed_sheet_data) - 1 - empty_rows_count} tasks for project {project_id}")

        return processed_task_ids
