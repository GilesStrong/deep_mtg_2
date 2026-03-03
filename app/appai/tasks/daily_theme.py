from datetime import datetime
from timeit import default_timer

import logfire
from appcards.constants.storage import THEME_COLLECTION_NAME
from appcards.models.deck import DailyDeckTheme
from appcore.modules.beartype import beartype
from appsearch.services.qdrant.upsert import create_collection_if_not_exists, upsert_documents
from celery import Task, shared_task
from django.db import transaction
from qdrant_client.http import models as qm

from appai.modules.dense_embedding import dense_embed
from appai.services.agents.deck_theme import get_daily_deck_theme


@shared_task(
    bind=True,
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
    soft_time_limit=3600,
    time_limit=4000,
    queue="llm",
    routing_key="llm",
)
@beartype
def make_daily_theme(self: Task) -> None:
    logfire.info(f"Starting daily theme generation task. Task ID: {self.request.id}")

    if DailyDeckTheme.objects.filter(date=datetime.now().date()).exists():
        logfire.info("Daily theme already exists for today. Exiting task.")
        return

    create_collection_if_not_exists(THEME_COLLECTION_NAME)

    start = default_timer()
    try:
        theme = get_daily_deck_theme()
        logfire.info(f"Generated daily theme: {theme}")
    except Exception as e:
        logfire.error(f"Error during daily theme generation task with ID: {self.request.id}: {e}")
        raise RuntimeError("Daily theme generation failed")
    time_taken = default_timer() - start
    logfire.info(f"Daily theme generation task with ID: {self.request.id} completed in {time_taken:.2f} seconds")

    embedding = dense_embed(theme.description)

    with transaction.atomic():
        daily_theme = DailyDeckTheme.objects.create(theme=theme.description)
        upsert_documents(
            THEME_COLLECTION_NAME,
            [
                qm.PointStruct(
                    id=str(daily_theme.id),
                    vector=embedding,
                    payload={
                        "description": theme.description,
                        "date": daily_theme.date.isoformat(),
                    },
                )
            ],
        )
