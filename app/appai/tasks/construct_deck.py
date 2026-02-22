import asyncio
from timeit import default_timer
from typing import Optional
from uuid import UUID

import logfire
from beartype import beartype
from celery import Task, shared_task

from appai.models.deck_build import DeckBuildStatus, DeckBuildTask
from appai.modules.construct_deck import construct_deck as _construct_deck


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
def construct_deck(
    self: Task, deck_description: str, deck_id: Optional[UUID] = None, available_set_codes: Optional[list[str]] = None
) -> None:
    logfire.info(
        f"Starting deck construction task with description: {deck_description} and deck_id: {deck_id}. Task ID: {self.request.id}"
    )
    DeckBuildTask.objects.filter(id=self.request.id).update(status=DeckBuildStatus.IN_PROGRESS)
    start = default_timer()
    asyncio.run(
        _construct_deck(
            deck_description=deck_description,
            deck_id=deck_id,
            available_set_codes=set(available_set_codes) if available_set_codes else None,
        )
    )
    DeckBuildTask.objects.filter(id=self.request.id).update(status=DeckBuildStatus.COMPLETED)
    time_taken = default_timer() - start
    logfire.info(f"Deck construction task with ID: {self.request.id} completed in {time_taken:.2f} seconds")
