from functools import lru_cache
from typing import Any, cast

import requests
from app.app_settings import APP_SETTINGS
from app.utils import in_celery_task
from beartype import beartype
from celery.result import AsyncResult


@lru_cache(maxsize=128)
@beartype
def _dense_embed(text: str) -> list[float]:
    response = requests.post(
        f"{APP_SETTINGS.OLLAMA_BASE_URL}/api/embeddings",
        json={"model": APP_SETTINGS.EMBEDDING_MODEL, "prompt": text},
        timeout=60,
    )
    response.raise_for_status()
    return response.json()["embedding"]


@beartype
def dense_embed(text: str) -> list[float]:
    if in_celery_task():
        from appai.tasks.dense_embedding import dense_embed as _dense_embed_task

        result: AsyncResult = cast(Any, _dense_embed_task.delay)(text)
        return cast(list[float], result.get(timeout=60))
    else:
        return _dense_embed(text)
