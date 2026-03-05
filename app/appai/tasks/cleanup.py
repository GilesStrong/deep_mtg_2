from datetime import datetime, timedelta

import logfire
from appcards.models.deck import Deck
from celery import Task, shared_task

from appai.models.deck_build import DeckBuildStatus, DeckBuildTask


@shared_task(
    bind=True,
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
    soft_time_limit=30,
    time_limit=90,
    queue="default",
    routing_key="default",
)
def cleanup_old_deck_build_tasks(self: Task) -> None:
    # cleanup old deck build tasks that have been in progress for more than 2 hours, marking them as failed
    in_progress_statuses = [
        DeckBuildStatus.IN_PROGRESS,
        DeckBuildStatus.BUILDING_DECK,
        DeckBuildStatus.CLASSIFYING_DECK_CARDS,
        DeckBuildStatus.FINDING_REPLACEMENT_CARDS,
    ]
    old_tasks = DeckBuildTask.objects.filter(
        status__in=in_progress_statuses, updated_at__lt=datetime.now() - timedelta(hours=2)
    )
    old_task_count = old_tasks.count()
    old_tasks.update(status=DeckBuildStatus.FAILED)
    logfire.info(f"Cleaned up {old_task_count} old deck build tasks that were in progress for more than 2 hours")

    # Cleanup empty failed decks
    old_failed_decks = Deck.objects.filter(
        valid=False, created_at__lt=datetime.now() - timedelta(days=1), cards__isnull=True
    )
    old_failed_deck_count = old_failed_decks.count()
    old_failed_decks.delete()
    logfire.info(
        f"Cleaned up {old_failed_deck_count} old failed decks that were created more than 1 day ago and have no cards"
    )
