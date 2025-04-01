import json
import os


class Storage:
    def __init__(self, storage_dir="storage"):
        self.storage_dir = storage_dir
        os.makedirs(self.storage_dir, exist_ok=True)
        self.users_file = os.path.join(self.storage_dir, "users.json")
        self.projects_file = os.path.join(self.storage_dir, "projects.json")
        self.tasks_file = os.path.join(self.storage_dir, "tasks.json")

        if not os.path.exists(self.users_file):
            with open(self.users_file, "w") as f:
                json.dump({}, f)

        if not os.path.exists(self.projects_file):
            with open(self.projects_file, "w") as f:
                json.dump({}, f)

        if not os.path.exists(self.tasks_file):
            with open(self.tasks_file, "w") as f:
                json.dump({}, f)

    def get_all_users(self):
        try:
            with open(self.users_file, "r") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def get_all_projects(self):
        try:
            with open(self.projects_file, "r") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def get_user_data(self, user_id):
        user_id = str(user_id)
        users = self.get_all_users()
        return users.get(user_id)

    def save_user_data(self, user_data):
        user_id = str(user_data["user_id"])
        users = self.get_all_users()
        if user_id in users and "username" in user_data and user_data["username"]:
            users[user_id]["username"] = user_data["username"]
        users[user_id] = user_data
        with open(self.users_file, "w") as f:
            json.dump(users, f, indent=2)

    def add_project(self, project_data):
        project_id = project_data["project_id"]
        projects = self.get_all_projects()
        projects[project_id] = project_data
        with open(self.projects_file, "w") as f:
            json.dump(projects, f, indent=2)

    def get_project(self, project_id):
        projects = self.get_all_projects()
        return projects.get(project_id)

    def add_user_to_project(self, user_id, project_id, role, username):
        user_id = str(user_id)
        user_data = self.get_user_data(user_id)
        if not user_data:
            user_data = {
                "user_id": user_id,
                "username": username,
                "projects": []
            }

        for proj in user_data.get("projects", []):
            if proj.get("project_id") == project_id:
                return False

        user_data.setdefault("projects", []).append({
            "project_id": project_id,
            "role": role
        })
        self.save_user_data(user_data)
        return True

    def get_user_projects(self, user_id):
        user_data = self.get_user_data(user_id)
        if not user_data or "projects" not in user_data:
            return []

        projects = self.get_all_projects()
        user_projects = []

        for user_project in user_data["projects"]:
            project_id = user_project["project_id"]
            if project_id in projects:
                project = projects[project_id].copy()
                project["role"] = user_project["role"]
                user_projects.append(project)

        return user_projects

    def get_all_tasks(self):
        try:
            with open(self.tasks_file, "r") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def get_project_tasks(self, project_id):
        tasks = self.get_all_tasks()
        return {task_id: task for task_id, task in tasks.items()
                if task.get("project_id") == project_id}

    def get_task(self, task_id):
        tasks = self.get_all_tasks()
        return tasks.get(task_id)

    def save_task(self, task):
        tasks = self.get_all_tasks()
        tasks[task["task_id"]] = task
        with open(self.tasks_file, "w") as f:
            json.dump(tasks, f, indent=2)

    def delete_task(self, task_id):
        tasks = self.get_all_tasks()
        if task_id in tasks:
            del tasks[task_id]
            with open(self.tasks_file, "w") as f:
                json.dump(tasks, f, indent=2)
            return True
        return False

    def get_user_tasks(self, user_id, project_id=None):
        user_data = self.get_user_data(user_id)
        if not user_data or "username" not in user_data:
            return []

        username = user_data["username"]
        tasks = self.get_all_tasks()
        user_tasks = []

        for task_id, task in tasks.items():
            if ((not project_id or task.get("project_id") == project_id) and
                    task.get("assignee", "").strip() == "@" + username):
                user_tasks.append(task)

        return user_tasks
