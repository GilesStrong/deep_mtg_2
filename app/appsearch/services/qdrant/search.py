from typing import Optional

from app.app_settings import APP_SETTINGS
from appai.modules.dense_embedding import dense_embed
from beartype import beartype
from qdrant_client.http import models as qm

from appsearch.services.qdrant.client import QDRANT_CLIENT
from appsearch.services.qdrant.search_dsl import Query as DSLQuery


@beartype
def run_query(
    collection_name: str, query_vector: Optional[list[float]], query_filter: Optional[qm.Filter], limit: int = 10
) -> list[qm.ScoredPoint]:
    res = QDRANT_CLIENT.query_points(
        collection_name=collection_name,
        query=query_vector,
        using="dense",
        query_filter=query_filter,
        search_params=qm.SearchParams(hnsw_ef=APP_SETTINGS.HNSW_EF_SEARCH),
        limit=limit,
        with_payload=True,
        with_vectors=False,
    )
    return res.points


@beartype
def run_query_from_dsl(collection_name: str, dsl_query: DSLQuery) -> list[qm.ScoredPoint]:
    query_vector = dense_embed(dsl_query.query_string) if dsl_query.query_string else None
    filter = dsl_query.filter.to_qdrant() if dsl_query.filter else None
    return run_query(
        collection_name=collection_name,
        query_vector=query_vector,
        query_filter=filter,
        limit=dsl_query.limit,
    )
