import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
import sys
import os

# Thêm root path để import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app
from deps import get_current_user

# --- 1. MOCK AUTHENTICATION ---
#Giả định user luôn là "test_user_123"
def override_get_current_user():
    return "test_user_123"

app.dependency_overrides[get_current_user] = override_get_current_user

# --- 2. MOCK VECTORIZER ---
# Ngăn hệ thống load model AI nặng nề khi chạy test
@pytest.fixture(scope="session", autouse=True)
def mock_vectorizer_load():
    with patch("modules.vectorizer.HybridVectorizer.load_fitted_tfidf") as mock_load:
        yield mock_load

# --- 3. TEST CLIENT ---
@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c
