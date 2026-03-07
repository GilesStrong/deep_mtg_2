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

from datetime import timedelta

import logfire
from appcards.models.deck import Deck
from celery import Task, shared_task
from django.utils import timezone

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
        status__in=in_progress_statuses, updated_at__lt=timezone.now() - timedelta(hours=2)
    )
    old_task_count = old_tasks.count()
    old_tasks.update(status=DeckBuildStatus.FAILED)
    logfire.info(f"Cleaned up {old_task_count} old deck build tasks that were in progress for more than 2 hours")

    # Cleanup empty failed decks
    old_failed_decks = Deck.objects.filter(
        valid=False, created_at__lt=timezone.now() - timedelta(days=1), cards__isnull=True
    )
    old_failed_deck_count = old_failed_decks.count()
    old_failed_decks.delete()
    logfire.info(
        f"Cleaned up {old_failed_deck_count} old failed decks that were created more than 1 day ago and have no cards"
    )
