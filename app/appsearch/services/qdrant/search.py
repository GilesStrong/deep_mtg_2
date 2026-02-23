from typing import Optional

import logfire
from app.app_settings import APP_SETTINGS
from appai.modules.dense_embedding import dense_embed
from beartype import beartype
from qdrant_client.http import models as qm

from appsearch.services.qdrant.client import QDRANT_CLIENT
from appsearch.services.qdrant.search_dsl import Query as DSLQuery


@beartype
def run_query(
    collection_name: str,
    query_vector: Optional[list[float]],
    query_filter: Optional[qm.Filter],
    limit: int = 10,
) -> list[qm.ScoredPoint]:
    log_message = f"Running query on collection '{collection_name}' with limit {limit}"
    if query_filter:
        log_message += f", using query_filter: {query_filter.model_dump_json(indent=2, ensure_ascii=False)}"
    else:
        log_message += ", with no query_filter"
    if query_vector:
        log_message += ", using query_vector"
    else:
        log_message += ", with no query_vector"
    logfire.info(log_message)
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
def run_query_from_dsl(
    dsl_query: DSLQuery, exclude_ids: Optional[list[str]] = None, include_ids: Optional[list[str]] = None
) -> list[qm.ScoredPoint]:
    query_vector = dense_embed(dsl_query.query_string) if dsl_query.query_string else None
    query_filter = dsl_query.filter.to_qdrant() if dsl_query.filter else None

    must_not = [qm.HasIdCondition(has_id=exclude_ids)] if exclude_ids else []  # type: ignore [arg-type]
    must = [qm.HasIdCondition(has_id=include_ids)] if include_ids else []  # type: ignore [arg-type]
    if query_filter:
        if query_filter.must:
            if isinstance(query_filter.must, list):
                query_filter.must.extend(must)
            else:
                query_filter.must = [query_filter.must] + must  # type: ignore [operator]
        else:
            query_filter.must = must  # type: ignore [assignment]
        if query_filter.must_not:
            if isinstance(query_filter.must_not, list):
                query_filter.must_not.extend(must_not)
            else:
                query_filter.must_not = [query_filter.must_not] + must_not  # type: ignore [operator]
        else:
            query_filter.must_not = must_not  # type: ignore [assignment]
    must = []

    return run_query(
        collection_name=dsl_query.collection_name,
        query_vector=query_vector,
        query_filter=query_filter,
        limit=dsl_query.limit,
    )
