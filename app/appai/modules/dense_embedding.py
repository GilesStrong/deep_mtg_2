# Copyright 2026 Giles Strong
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from functools import lru_cache
from typing import Any, cast

import requests
from app.app_settings import APP_SETTINGS
from app.utils import in_celery_task
from appcore.modules.beartype import beartype
from celery.result import AsyncResult


@lru_cache(maxsize=128)
@beartype
def _dense_embed(text: str) -> list[float]:
    """
    Generate a dense vector embedding for the given text using the Ollama embeddings API.
    Do not call this function directly; use the `dense_embed` function instead, which handles asynchronous execution when called within a Celery task.

    Args:
        text (str): The input text to be embedded.

    Returns:
        list[float]: A list of floating-point numbers representing the dense vector
            embedding of the input text.

    Raises:
        requests.exceptions.HTTPError: If the API request fails or returns an error
            status code.
        requests.exceptions.Timeout: If the API request exceeds the 60-second timeout.
        KeyError: If the response JSON does not contain the expected 'embedding' key.
    """
    response = requests.post(
        f"{APP_SETTINGS.OLLAMA_BASE_URL}/api/embeddings",
        json={"model": APP_SETTINGS.EMBEDDING_MODEL, "prompt": text},
        timeout=60,
    )
    response.raise_for_status()
    return response.json()["embedding"]


@beartype
def dense_embed(text: str) -> list[float]:
    """
    Generates a dense embedding vector for the given text.

    This function handles two execution contexts:
    - When running outside a Celery task, it delegates the embedding generation
        to a Celery worker task asynchronously, waiting up to 60 seconds for the result.
    - When running inside a Celery task, it directly calls the underlying
        embedding function.

    Args:
            text (str): The input text to be embedded.

    Returns:
            list[float]: A list of floating point numbers representing the dense
                    embedding vector of the input text.

    Raises:
            celery.exceptions.TimeoutError: If the Celery task does not complete
                    within the 60-second timeout window.
    """
    if in_celery_task():
        return _dense_embed(text)
    else:
        from appai.tasks.dense_embedding import dense_embed as _dense_embed_task

        result: AsyncResult = cast(Any, _dense_embed_task.delay)(text)
        return cast(list[float], result.get(timeout=60))
