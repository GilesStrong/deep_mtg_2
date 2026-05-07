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

from __future__ import annotations

from datetime import timedelta
from unittest.mock import MagicMock, patch

from django.test import TestCase
from django.utils import timezone

from appai.models.memory import Memory, MemoryMaintenanceReport
from appai.tasks.memory_maintenance import MIN_MEMORIES_FOR_MAINTENANCE, run_memory_maintenance_task

_MODULE = "appai.tasks.memory_maintenance"


class RunMemoryMaintenanceTaskTests(TestCase):
    """Tests for the run_memory_maintenance_task Celery task."""

    def _create_report(self, days_ago: int = 0) -> MemoryMaintenanceReport:
        """Create a MemoryMaintenanceReport with created_at set to a given number of days ago.

        Args:
            days_ago: How many days before now to set the created_at timestamp.

        Returns:
            The created MemoryMaintenanceReport instance.
        """
        report = MemoryMaintenanceReport.objects.create(report={})
        if days_ago:
            MemoryMaintenanceReport.objects.filter(pk=report.pk).update(
                created_at=timezone.now() - timedelta(days=days_ago)
            )
            report.refresh_from_db()
        return report

    def _create_memories(self, count: int, created_at: timezone.datetime | None = None) -> None:
        """Create a number of Memory objects, optionally overriding created_at.

        Args:
            count: Number of Memory objects to create.
            created_at: Optional timestamp to backdate all created memories to.
        """
        for i in range(count):
            Memory.objects.create(name=f"Memory {i}", text=f"Content {i}")
        if created_at is not None:
            Memory.objects.update(created_at=created_at)

    @patch(f"{_MODULE}.asyncio.run")
    @patch(f"{_MODULE}.run_memory_maintenance", new_callable=MagicMock)
    def test_runs_when_no_previous_report(self, mock_run_maintenance, mock_asyncio_run):
        """
        GIVEN no MemoryMaintenanceReport exists
        WHEN run_memory_maintenance_task runs
        THEN it calls run_memory_maintenance via asyncio.run
        """
        run_memory_maintenance_task.run()

        mock_run_maintenance.assert_called_once()
        mock_asyncio_run.assert_called_once()

    @patch(f"{_MODULE}.asyncio.run")
    @patch(f"{_MODULE}.run_memory_maintenance", new_callable=MagicMock)
    def test_skips_when_latest_report_is_from_today(self, mock_run_maintenance, mock_asyncio_run):
        """
        GIVEN a MemoryMaintenanceReport exists with created_at today
        WHEN run_memory_maintenance_task runs
        THEN it returns early without calling run_memory_maintenance
        """
        self._create_report(days_ago=0)

        run_memory_maintenance_task.run()

        mock_run_maintenance.assert_not_called()
        mock_asyncio_run.assert_not_called()

    @patch(f"{_MODULE}.asyncio.run")
    @patch(f"{_MODULE}.run_memory_maintenance", new_callable=MagicMock)
    def test_skips_when_too_few_new_memories_since_last_maintenance(self, mock_run_maintenance, mock_asyncio_run):
        """
        GIVEN a MemoryMaintenanceReport exists from yesterday
          AND fewer than MIN_MEMORIES_FOR_MAINTENANCE new memories have been created since
        WHEN run_memory_maintenance_task runs
        THEN it returns early without calling run_memory_maintenance
        """
        report = self._create_report(days_ago=1)
        self._create_memories(
            MIN_MEMORIES_FOR_MAINTENANCE - 1,
            created_at=report.created_at + timedelta(hours=1),
        )

        run_memory_maintenance_task.run()

        mock_run_maintenance.assert_not_called()
        mock_asyncio_run.assert_not_called()

    @patch(f"{_MODULE}.asyncio.run")
    @patch(f"{_MODULE}.run_memory_maintenance", new_callable=MagicMock)
    def test_runs_when_enough_new_memories_since_last_maintenance(self, mock_run_maintenance, mock_asyncio_run):
        """
        GIVEN a MemoryMaintenanceReport exists from yesterday
          AND at least MIN_MEMORIES_FOR_MAINTENANCE new memories have been created since
        WHEN run_memory_maintenance_task runs
        THEN it calls run_memory_maintenance via asyncio.run
        """
        report = self._create_report(days_ago=1)
        self._create_memories(
            MIN_MEMORIES_FOR_MAINTENANCE,
            created_at=report.created_at + timedelta(hours=1),
        )

        run_memory_maintenance_task.run()

        mock_run_maintenance.assert_called_once()
        mock_asyncio_run.assert_called_once()

    @patch(f"{_MODULE}.asyncio.run", side_effect=Exception("LLM failure"))
    @patch(f"{_MODULE}.run_memory_maintenance", new_callable=MagicMock)
    def test_raises_runtime_error_when_maintenance_fails(self, _mock_run_maintenance, _mock_asyncio_run):
        """
        GIVEN no previous MemoryMaintenanceReport exists
        WHEN run_memory_maintenance raises an exception
        THEN a RuntimeError is raised by the task
        """
        with self.assertRaises(RuntimeError):
            run_memory_maintenance_task.run()
