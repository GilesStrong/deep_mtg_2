from app.app_settings import APP_SETTINGS
from qdrant_client import QdrantClient


def _get_client() -> QdrantClient:
    return QdrantClient(url=APP_SETTINGS.QDRANT_URL)


QDRANT_CLIENT = _get_client()
