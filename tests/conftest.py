import pytest
import os
import shutil
from src.utils.storage import Storage

@pytest.fixture
def test_storage():
    test_dir = "test_storage"
    storage = Storage(storage_dir=test_dir)
    yield storage
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)