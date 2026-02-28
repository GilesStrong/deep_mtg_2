import os
import sys
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


type ENV = Literal['development', 'staging', 'production']


class EnvSettings(BaseSettings):
    DEBUG: bool
    ENVIRONMENT: ENV
    LOCALITY: str


class RedisSettings(BaseSettings):
    REDIS_URL: str


class DjangoSettings(BaseSettings):
    SECRET_KEY: str
    DEBUG: bool
    ALLOWED_HOSTS: list[str]
    CSRF_TRUSTED_ORIGINS: list[str]


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
    TOOL_MODEL: str
    EMBEDDING_MODEL: str
    EMBEDDING_DIMENSION: int
    GOOGLE_API_KEY: str
    DEEPSEEK_API_KEY: str
    MAX_AGENT_CALLS_PER_TASK: int


class QdrantSettings(BaseSettings):
    QDRANT_URL: str
    HNSW_M: int
    HNSW_EF_CONSTRUCT: int
    HNSW_EF_SEARCH: int


class LogfireSettings(BaseSettings):
    LOGFIRE_TOKEN: str
    LOGFIRE_ENVIRONMENT: str


class GoogleAuthSettings(BaseSettings):
    GOOGLE_CLIENT_ID: str
    GOOGLE_CLIENT_SECRET: str


class AuthSettings(BaseSettings):
    JWT_ISSUER: str
    JWT_AUDIENCE: str
    JWT_SIGNING_KEY: str
    ACCESS_TOKEN_TTL_SECONDS: int
    REFRESH_TOKEN_TTL_SECONDS: int


class LimitSettings(BaseSettings):
    DECK_BUILDS_PER_DAY: int


class GuardrailSettings(BaseSettings):
    RELEVANCY_THRESHOLD: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="A value between 0.0 and 1.0 indicating the relevance threshold below which a user's request will be blocked.",
    )
    N_WARNINGS_BEFORE_BLOCK: int = Field(
        ...,
        ge=1,
        description="The number of warnings a user can receive before their request is blocked.",
    )


class AppSettings(
    GoogleAuthSettings,
    EnvSettings,
    DjangoSettings,
    CelerySettings,
    PostgresSettings,
    AISettings,
    QdrantSettings,
    LogfireSettings,
    AuthSettings,
    LimitSettings,
    RedisSettings,
    GuardrailSettings,
):
    model_config = SettingsConfigDict(env_file_encoding='utf-8')


def _find_named_env_file(filename: str) -> Path | None:
    current_dir = BASE_DIR
    for _ in range(5):
        env_file_path = current_dir / filename
        if env_file_path.is_file():
            return env_file_path
        current_dir = current_dir.parent
    return None


def find_env_file() -> Path | None:
    return _find_named_env_file('.env')


def find_tests_env_file() -> Path | None:
    return _find_named_env_file('.env.tests')


def _resolve_custom_env_file(path_value: str) -> Path | None:
    candidate = Path(path_value)
    if candidate.is_absolute() and candidate.is_file():
        return candidate

    candidates = [
        Path.cwd() / candidate,
        BASE_DIR / candidate,
        BASE_DIR.parent / candidate,
    ]
    for c in candidates:
        if c.is_file():
            return c
    return None


def get_app_settings() -> AppSettings:
    custom_env_file = os.getenv("APP_ENV_FILE")
    if custom_env_file:
        env_file_path = _resolve_custom_env_file(custom_env_file)
        if env_file_path:
            return AppSettings(_env_file=env_file_path)  # type: ignore[call-arg]

    is_testing = "pytest" in sys.modules or "test" in sys.argv
    env_file_path = find_tests_env_file() if is_testing else find_env_file()
    if env_file_path is None:
        env_file_path = find_env_file()

    if env_file_path:
        return AppSettings(_env_file=env_file_path)  # type: ignore[call-arg]
    else:
        print("Warning: no env file found (.env.tests/.env). Using default environment variables.")
        return AppSettings()  # type: ignore[call-arg]


APP_SETTINGS = get_app_settings()
