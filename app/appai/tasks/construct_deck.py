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

import asyncio
from timeit import default_timer
from typing import Optional
from uuid import UUID

import logfire
from app.utils import celery_task_context
from appcore.modules.beartype import beartype
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
    self: Task,
    deck_description: str,
    user_id: str,
    deck_id: Optional[str] = None,
    available_set_codes: Optional[list[str]] = None,
) -> None:
    with celery_task_context():
        with logfire.span("build_deck_task", task_id=self.request.id, user_id=user_id, deck_id=deck_id):
            logfire.info(
                f"Starting deck construction task with description: {deck_description} and deck_id: {deck_id}. Task ID: {self.request.id}"
            )
            if deck_id is not None:
                deck_uuid = UUID(str(deck_id))
            else:
                deck_uuid = None
            DeckBuildTask.objects.filter(id=self.request.id).update(status=DeckBuildStatus.IN_PROGRESS)
            start = default_timer()
            try:
                asyncio.run(
                    _construct_deck(
                        deck_description=deck_description,
                        deck_id=deck_uuid,
                        user_id=UUID(user_id),
                        build_task_id=UUID(self.request.id),
                        available_set_codes=set(available_set_codes) if available_set_codes else None,
                    )
                )
            except Exception as e:
                logfire.error(f"Error during deck construction task with ID: {self.request.id}: {e}")
                DeckBuildTask.objects.filter(id=self.request.id).update(status=DeckBuildStatus.FAILED)
                raise RuntimeError("Deck construction failed")
            DeckBuildTask.objects.filter(id=self.request.id).update(status=DeckBuildStatus.COMPLETED)
            time_taken = default_timer() - start
            logfire.info(f"Deck construction task with ID: {self.request.id} completed in {time_taken:.2f} seconds")
