# tests/test_config.py
import pytest
import os
import importlib
from unittest.mock import patch
from core import config

# 1. TEST THIẾU MONGO_URI (Cover dòng raise ValueError MONGO)
def test_config_missing_mongo_uri():
    with patch.dict(os.environ, {"MONGO_URI": ""}, clear=False):
        with pytest.raises(ValueError, match="Thiếu biến MONGO_URI"):
            importlib.reload(config)

# 2. TEST THIẾU SECRET_KEY (Cover dòng raise ValueError SECRET)
def test_config_missing_secret_key():
    env_vars = {
        "MONGO_URI": "mongodb://localhost:27017",
        "SECRET_KEY": "" # Rỗng
    }
    with patch.dict(os.environ, env_vars, clear=False):
        with pytest.raises(ValueError, match="Thiếu biến SECRET_KEY"):
            importlib.reload(config)

# 3. TEST THIẾU GOOGLE_CLIENT_ID (Cover dòng print CẢNH BÁO)
def test_config_missing_google_id(capsys):
    env_vars = {
        "MONGO_URI": "mongodb://localhost:27017",
        "SECRET_KEY": "mysecret",
        "GOOGLE_CLIENT_ID": "" # Rỗng
    }
    
    with patch.dict(os.environ, env_vars, clear=False):
        importlib.reload(config)
        captured = capsys.readouterr()
        assert "CẢNH BÁO: Thiếu GOOGLE_CLIENT_ID" in captured.out