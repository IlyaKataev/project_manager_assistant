import pytest
from unittest.mock import Mock
import os
import shutil
from src.utils.storage import Storage
from src.reminders.reminder_service import ReminderService


@pytest.fixture
def test_storage():
    test_dir = "test_storage"
    storage = Storage(storage_dir=test_dir)
    yield storage
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)


@pytest.fixture
def mock_bot():
    return Mock()
