import logging
import sys

def setup_logging():
    logger = logging.getLogger("album_gen")
    logger.setLevel(logging.INFO)
    
    # Console Handler (Visible in Vercel Dashboard)
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter('%(levelname)s: %(message)s')
    handler.setFormatter(formatter)
    
    logger.addHandler(handler)
    return logger

logger = setup_logging()