from typing import Any

import requests
from app.app_settings import APP_SETTINGS
from appsearch.services.qdrant.client import QDRANT_CLIENT
from django.core.management.base import BaseCommand
from qdrant_client.http import models as qm

from appcards.constants.storage import CARD_COLLECTION_NAME


class Command(BaseCommand):
    help = 'Generate LLM embeddings for cards without embeddings'

    def handle(self, *args: Any, **options: Any) -> None:
        def embed_query(text: str) -> list[float]:
            r = requests.post(
                f"{APP_SETTINGS.OLLAMA_BASE_URL}/api/embeddings",
                json={"model": APP_SETTINGS.EMBEDDING_MODEL, "prompt": text},
                timeout=60,
            )
            r.raise_for_status()
            return r.json()["embedding"]

        query_text = "cheap red instant that deals damage"
        query_vector = embed_query(query_text)

        flt = qm.Filter(
            must=[
                qm.FieldCondition(key="colors", match=qm.MatchAny(any=["R"])),
                qm.FieldCondition(key="types", match=qm.MatchAny(any=["Instant"])),
                qm.FieldCondition(key="converted_mana_cost", range=qm.Range(lte=2)),
            ]
        )

        res = QDRANT_CLIENT.query_points(
            collection_name=CARD_COLLECTION_NAME,
            query=query_vector,  # <-- dense vector
            using="dense",  # <-- choose the named vector
            query_filter=flt,  # <-- filters live here
            search_params=qm.SearchParams(hnsw_ef=128),
            limit=10,
            with_payload=True,
            with_vectors=False,
        )

        for p in res.points:
            print(p.id, p.score, p.payload.get("name"))
