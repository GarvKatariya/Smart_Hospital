from pydantic_settings import BaseSettings, SettingsConfigDict
import os

# Project root is one level above the backend directory
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

class Settings(BaseSettings):
    DATABASE_URL: str = f'sqlite:///{os.path.join(PROJECT_ROOT, "hospital.db")}'
    SECRET_KEY: str = "supersecretkey"  # Default for dev if not in .env
    ALGORITHM: str = 'HS256'
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    GEMINI_API_KEY: str = ''
    LLM_PROVIDER: str = 'gemini'
    DEMO_MODE: bool = True
    DEBUG: bool = True
    HOST: str = '0.0.0.0'
    BACKEND_PORT: int = 8000
    UPLOAD_DIR: str = os.path.join(PROJECT_ROOT, 'uploads')
    MAX_UPLOAD_SIZE_MB: int = 10
    FAISS_INDEX_DIR: str = os.path.join(PROJECT_ROOT, 'rag', 'index')
    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 50
    EMBEDDING_MODEL: str = 'all-MiniLM-L6-v2'
    RETRIEVAL_TOP_K: int = 5
    TOTAL_HOSPITAL_BEDS: int = 200
    OCCUPANCY_WARNING_THRESHOLD: int = 85

    model_config = SettingsConfigDict(
        env_file=os.path.join(PROJECT_ROOT, '.env'),
        env_file_encoding='utf-8',
        extra='ignore',
    )

settings = Settings()

