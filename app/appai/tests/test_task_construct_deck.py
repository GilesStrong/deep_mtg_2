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

from unittest.mock import MagicMock, patch
from uuid import UUID

from django.test import TestCase

from appai.models.deck_build import DeckBuildStatus
from appai.tasks.construct_deck import construct_deck

_MODULE = "appai.tasks.construct_deck"
_TASK_ID = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
_DECK_ID = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
_USER_ID = UUID("12345678-1234-5678-1234-567812345678")


class ConstructDeckTaskTests(TestCase):
    """Tests for the construct_deck Celery task wrapper."""

    @patch(f"{_MODULE}.default_timer", side_effect=[10.0, 13.5])
    @patch(f"{_MODULE}.asyncio.run")
    @patch(f"{_MODULE}.DeckBuildTask")
    def test_updates_status_and_runs_module_construct_deck(self, mock_build_task, mock_asyncio_run, _mock_timer):
        """
        GIVEN a valid task request with deck/user IDs and optional set codes
        WHEN construct_deck task executes successfully
        THEN it marks IN_PROGRESS, runs the async builder with converted UUID inputs, and marks COMPLETED
        """
        queryset = MagicMock()
        mock_build_task.objects.filter.return_value = queryset

        with patch(f"{_MODULE}._construct_deck", new=MagicMock()) as mock_construct_deck:
            with patch.object(construct_deck.request, "id", str(_TASK_ID)):
                construct_deck(
                    deck_description="mono-red aggro",
                    deck_id=str(_DECK_ID),
                    user_id=str(_USER_ID),
                    available_set_codes=["FDN", "BLB"],
                )

        mock_build_task.objects.filter.assert_called_with(id=str(_TASK_ID))
        self.assertEqual(
            queryset.update.call_args_list[0].kwargs,
            {"status": DeckBuildStatus.IN_PROGRESS},
        )
        self.assertEqual(
            queryset.update.call_args_list[-1].kwargs,
            {"status": DeckBuildStatus.COMPLETED},
        )
        mock_construct_deck.assert_called_once_with(
            deck_description="mono-red aggro",
            deck_id=_DECK_ID,
            user_id=_USER_ID,
            build_task_id=_TASK_ID,
            available_set_codes={"FDN", "BLB"},
        )
        mock_asyncio_run.assert_called_once()

    @patch(f"{_MODULE}.asyncio.run", side_effect=Exception("boom"))
    @patch(f"{_MODULE}.DeckBuildTask")
    def test_marks_failed_and_raises_runtime_error_on_exception(self, mock_build_task, _mock_asyncio_run):
        """
        GIVEN an exception raised while running the async deck constructor
        WHEN construct_deck task executes
        THEN it marks the build as FAILED and raises RuntimeError
        """
        queryset = MagicMock()
        mock_build_task.objects.filter.return_value = queryset

        with patch(f"{_MODULE}._construct_deck", new=MagicMock()) as mock_construct_deck:
            with patch.object(construct_deck.request, "id", str(_TASK_ID)):
                with self.assertRaises(RuntimeError):
                    construct_deck(
                        deck_description="mono-red aggro",
                        deck_id=str(_DECK_ID),
                        user_id=str(_USER_ID),
                        available_set_codes=None,
                    )

        self.assertIn(
            {"status": DeckBuildStatus.FAILED},
            [call.kwargs for call in queryset.update.call_args_list],
        )
        mock_construct_deck.assert_called_once()
