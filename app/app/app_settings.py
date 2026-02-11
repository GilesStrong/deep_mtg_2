from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


type ENV = Literal['development', 'staging', 'production']


class EnvSettings(BaseSettings):
    DEBUG: bool
    ENVIRONMENT: ENV


class DjangoSettings(BaseSettings):
    SECRET_KEY: str
    DEBUG: bool
    ALLOWED_HOSTS: list[str]


class CelerySettings(BaseSettings):
    CELERY_BROKER_URL: str
    CELERY_RESULT_BACKEND: str
    CELERY_TASK_DEFAULT_QUEUE: str
    CELERY_TASK_DEFAULT_EXCHANGE: str
    CELERY_TASK_DEFAULT_ROUTING_KEY: str
    CELERY_TASK_CREATE_MISSING_QUEUES: bool


class PostgresSettings(BaseSettings):
    POSTGRES_DB: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_HOST: str
    POSTGRES_PORT: int


class AISettings(BaseSettings):
    OLLAMA_BASE_URL: str
    OLLAMA_MAX_TOKENS: int
    OLLAMA_NUM_CTX: int
    TEXT_MODEL: str


class AppSettings(EnvSettings, DjangoSettings, CelerySettings, PostgresSettings, AISettings):
    model_config = SettingsConfigDict(env_file_encoding='utf-8')


def find_env_file() -> Path | None:
    current_dir = BASE_DIR
    for _ in range(5):
        env_file_path = current_dir / '.env'
        if env_file_path.is_file():
            return env_file_path
        current_dir = current_dir.parent
    return None


def get_app_settings() -> AppSettings:
    env_file_path = find_env_file()
    if env_file_path:
        return AppSettings(_env_file=env_file_path)  # type: ignore[call-arg]
    else:
        print("Warning: .env file not found. Using default environment variables.")
        return AppSettings()  # type: ignore[call-arg]


APP_SETTINGS = get_app_settings()
