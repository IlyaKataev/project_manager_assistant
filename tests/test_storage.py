def test_save_and_get_user_data(test_storage):
    user_data = {
        "user_id": "123456",
        "username": "test_user",
        "projects": []
    }

    test_storage.save_user_data(user_data)
    retrieved = test_storage.get_user_data("123456")

    assert retrieved["username"] == "test_user"
    assert retrieved["user_id"] == "123456"

def test_add_user_to_project(test_storage):
    project_data = {
        "project_id": "test_project",
        "google_sheets_id": "test_project",
        "sheet_name": "Test"
    }
    test_storage.add_project(project_data)

    result = test_storage.add_user_to_project(
        "123456",
        "test_project",
        "member",
        "test_user"
    )

    assert result is True

    user_data = test_storage.get_user_data("123456")
    assert len(user_data["projects"]) == 1
    assert user_data["projects"][0]["project_id"] == "test_project"

def test_get_user_projects(test_storage):
    user_id = "123456"
    user_data = {
        "user_id": user_id,
        "username": "test_user",
        "projects": []
    }
    test_storage.save_user_data(user_data)

    project_data = {
        "project_id": "test_project",
        "google_sheets_id": "gs123",
        "sheet_name": "Test Project"
    }
    test_storage.add_project(project_data)
    test_storage.add_user_to_project(user_id, "test_project", "owner", "test_user")

    projects = test_storage.get_user_projects(user_id)

    assert len(projects) == 1
    assert projects[0]["project_id"] == "test_project"
    assert projects[0]["google_sheets_id"] == "gs123"
    assert projects[0]["role"] == "owner"

def test_user_with_multiple_projects(test_storage):
    user_id = "123456"
    user_data = {
        "user_id": user_id,
        "username": "test_user",
        "projects": []
    }
    test_storage.save_user_data(user_data)

    projects = [
        {
            "project_id": "project1",
            "google_sheets_id": "gs1",
            "sheet_name": "Project 1"
        },
        {
            "project_id": "project2",
            "google_sheets_id": "gs2",
            "sheet_name": "Project 2"
        }
    ]

    for project in projects:
        test_storage.add_project(project)
        test_storage.add_user_to_project(user_id, project["project_id"], "member", "test_user")

    user_projects = test_storage.get_user_projects(user_id)

    assert len(user_projects) == 2
    assert {p["project_id"] for p in user_projects} == {"project1", "project2"}

def test_get_project(test_storage):
    project_data = {
        "project_id": "test_project",
        "google_sheets_id": "gs123",
        "sheet_name": "Test Project"
    }
    test_storage.add_project(project_data)

    project = test_storage.get_project("test_project")

    assert project is not None
    assert project["project_id"] == "test_project"
    assert project["google_sheets_id"] == "gs123"