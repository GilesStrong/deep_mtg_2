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

import logfire
from app.utils import celery_task_context
from celery import Task, shared_task
from django.utils import timezone

from appai.models.memory import Memory, MemoryMaintenanceReport
from appai.services.graphs.memory_maintenance import run_memory_maintenance

MIN_MEMORIES_FOR_MAINTENANCE = 10


@shared_task(
    bind=True,
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
    soft_time_limit=3600,
    time_limit=4000,
    queue="llm",
    routing_key="llm",
)
def run_memory_maintenance_task(self: Task) -> None:
    """
    Runs the daily memory maintenance process, which removes duplicate and outdated memories, to ensure the memory system remains efficient and relevant.
    The task only runs up to once a day, and only if a minimum number of new memories have been created since the last maintenance, to avoid unnecessary runs.

    Args:
        self (Task): The Celery task instance, providing access to task metadata
            such as `self.request.id`.

    Raises:
        RuntimeError: If an error occurs during the process.
    """
    latest_report = MemoryMaintenanceReport.objects.order_by('-created_at').first()
    if latest_report:
        if latest_report.created_at.date() == timezone.now().date():
            return

        n_memories_since_last_maintenance = Memory.objects.filter(created_at__gte=latest_report.created_at).count()
        if n_memories_since_last_maintenance < MIN_MEMORIES_FOR_MAINTENANCE:
            logfire.info(
                f"Skipping memory maintenance task with ID: {self.request.id} because only {n_memories_since_last_maintenance} new memories have been created since the last maintenance, which is below the threshold of {MIN_MEMORIES_FOR_MAINTENANCE}."
            )
            return

    with celery_task_context():
        logfire.info(f"Starting daily memory maintenance task. Task ID: {self.request.id}")

        start = default_timer()
        try:
            asyncio.run(run_memory_maintenance())
        except Exception as e:
            logfire.error(f"Error during daily memory maintenance task with ID: {self.request.id}: {e}")
            raise RuntimeError("Daily memory maintenance failed")
        time_taken = default_timer() - start
        logfire.info(f"Daily memory maintenance task with ID: {self.request.id} completed in {time_taken:.2f} seconds")
