import requests
from app.app_settings import APP_SETTINGS
from beartype import beartype


@beartype
def dense_embed(text: str) -> list[float]:
    response = requests.post(
        f"{APP_SETTINGS.OLLAMA_BASE_URL}/api/embeddings",
        json={"model": APP_SETTINGS.EMBEDDING_MODEL, "prompt": text},
        timeout=60,
    )
    response.raise_for_status()
    return response.json()["embedding"]
