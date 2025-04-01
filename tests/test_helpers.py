import re
from src.utils.helpers import extract_spreadsheet_id, ensure_user_data


def test_extract_spreadsheet_id_with_different_url_formats():
    urls = [
        "https://docs.google.com/spreadsheets/d/abc123xyz/edit#gid=0",
        "https://docs.google.com/spreadsheets/d/abc123xyz/",
        "https://docs.google.com/spreadsheets/d/abc123xyz",
        "docs.google.com/spreadsheets/d/abc123xyz"
    ]
    for url in urls:
        assert extract_spreadsheet_id(url) == "abc123xyz"


def test_extract_spreadsheet_id_with_invalid_inputs():
    invalid_inputs = [
        "",
        "https://yandex.ru",
        None,
    ]
    for input_value in invalid_inputs:
        assert extract_spreadsheet_id(input_value) is None


def test_ensure_user_data_create(test_storage):
    user = test_storage.get_user_data("1")
    assert user is None
    ensure_user_data(test_storage, "1", "testuser")
    user = test_storage.get_user_data("1")
    assert user is not None
    assert user["username"] == "testuser"


def test_ensure_user_data_update(test_storage):
    ensure_user_data(test_storage, "2", "olduser")
    result = ensure_user_data(test_storage, "2", "newuser")
    user, updated = result
    assert updated is True
    assert user["username"] == "newuser"


def test_ensure_user_data_no_update(test_storage):
    ensure_user_data(test_storage, "3", "user")
    result = ensure_user_data(test_storage, "3", "user")
    user, updated = result
    assert updated is False
    assert user["username"] == "user"
