from timeit import default_timer

import logfire
from app.utils import celery_task_context
from appcards.constants.storage import THEME_COLLECTION_NAME
from appcards.models.deck import DailyDeckTheme
from appsearch.services.qdrant.upsert import create_collection_if_not_exists, upsert_documents
from celery import Task, shared_task
from django.db import transaction
from django.utils import timezone
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
def make_daily_theme(self: Task) -> None:
    """
    Generate and store a daily deck theme for Magic: The Gathering.

    This method is designed to be used as a Celery task and will early-return if a
    theme has already been generated for the current date.

    Args:
        self (Task): The Celery task instance, providing access to task metadata
            such as `self.request.id`.

    Raises:
        RuntimeError: If an error occurs during the theme generation process.
    """
    if DailyDeckTheme.objects.filter(date=timezone.now().date()).exists():
        return

    with celery_task_context():
        logfire.info(f"Starting daily theme generation task. Task ID: {self.request.id}")
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
            try:
                daily_theme = DailyDeckTheme.objects.create(theme=theme.description)
                upsert_documents(
                    THEME_COLLECTION_NAME,
                    [
                        qm.PointStruct(
                            id=str(daily_theme.id),
                            vector={'dense': embedding},
                            payload={
                                "description": theme.description,
                                "date": daily_theme.date.isoformat(),
                            },
                        )
                    ],
                )
            except Exception as e:
                logfire.error(f"Error during database transaction for daily theme task with ID: {self.request.id}: {e}")
                raise RuntimeError("Failed to save daily theme to database and vector store")
