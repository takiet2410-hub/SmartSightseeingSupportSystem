from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8')

    # MongoDB
    MONGO_DB_URL: str
    MONGO_DB_NAME: str
    DESTINATIONS_COLLECTION: str
    
    # LLM
    GEMINI_API_KEY: str 
    GEMINI_MODEL_NAME: str

    # Data paths
    VECTORIZER_PATH: str
    EXCEL_FILE_PATH: str
    
    # OpenWeather
    OPENWEATHER_API_KEY: str
    
    SECRET_KEY: str 
    ALGORITHM: str 
    ACCESS_TOKEN_EXPIRE_MINUTES: int

# Khởi tạo một instance để các file khác có thể import
settings = Settings()