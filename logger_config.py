import logging
import sys
from pathlib import Path

from logging.handlers import RotatingFileHandler

LOG_DIR = Path(__file__).parent / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "app.log"

def setup_logging():
    logger = logging.getLogger("album_gen")
    logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(filename)s:%(lineno)d | %(message)s'
    )

    # 1. Console (Debug)
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.DEBUG)
    console.setFormatter(formatter)

    # 2. File (Info - For History)
    file_h = RotatingFileHandler(LOG_FILE, maxBytes=10*1024*1024, backupCount=5)
    file_h.setLevel(logging.INFO)
    file_h.setFormatter(formatter)

    if not logger.hasHandlers():
        logger.addHandler(console)
        logger.addHandler(file_h)
    
    return logger

logger = setup_logging()