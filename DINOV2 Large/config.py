from dotenv import load_dotenv
import os

load_dotenv("config.env")

MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("DB_NAME")
COLLECTION_NAME = os.getenv("COLLECTION_NAME")
DESTINATION_NAME = os.getenv("DESTINATION_NAME")
