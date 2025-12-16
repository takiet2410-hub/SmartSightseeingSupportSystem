# tests/conftest.py
import pytest
from fastapi.testclient import TestClient
from main import app
import importlib
from core import config

@pytest.fixture(scope="module")
def client():
    # Tạo client giả lập để gọi API
    with TestClient(app) as c:
        yield c

@pytest.fixture(autouse=True)
def restore_valid_config():
    yield
    # Quan trọng: Sau khi mỗi test case chạy xong,
    # reload lại config về trạng thái gốc để không ảnh hưởng test khác
    importlib.reload(config)