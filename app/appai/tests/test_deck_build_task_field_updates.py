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

from collections.abc import Awaitable, Callable
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

from django.test import TestCase

from appai.services.agents.tools.deck_tools import add_card_to_deck, clear_deck, remove_card_from_deck
from appai.services.agents.tools.query_tools import search_for_cards

_DECK_TOOLS_MODULE = "appai.services.agents.tools.deck_tools"
_QUERY_TOOLS_MODULE = "appai.services.agents.tools.query_tools"

_DECK_ID = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
_BUILD_TASK_ID = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
_CARD_ID = UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")


def _make_ctx() -> SimpleNamespace:
    """Build a minimal run context object for tool tests."""
    return SimpleNamespace(
        deps=SimpleNamespace(
            deck_id=_DECK_ID,
            build_task_id=_BUILD_TASK_ID,
            available_set_codes={"FDN"},
        )
    )


def _immediate_sync_to_async(func: Callable[..., object]) -> Callable[..., Awaitable[object]]:
    """Return a wrapper that executes sync functions immediately for tests."""

    async def _runner(*args, **kwargs) -> object:
        return func(*args, **kwargs)

    return _runner


class DeckToolDeckSizeUpdateTests(TestCase):
    """Tests for deck tool updates to DeckBuildTask.deck_size."""

    @patch(f"{_DECK_TOOLS_MODULE}.DeckBuildTask")
    @patch(f"{_DECK_TOOLS_MODULE}.DeckCard")
    @patch(f"{_DECK_TOOLS_MODULE}.Card")
    @patch(f"{_DECK_TOOLS_MODULE}.Deck")
    async def test_add_card_updates_deck_size(
        self, mock_deck_cls, mock_card_cls, mock_deck_card_cls, mock_task_cls
    ) -> None:
        """
        GIVEN a valid deck/card and an add-card operation
        WHEN add_card_to_deck runs
        THEN DeckBuildTask.deck_size is updated to the new total deck size
        """
        deck = MagicMock()
        deck.name = "Test Deck"
        card = MagicMock()
        card.name = "Lightning Bolt"
        deck_card = MagicMock()
        deck_card.quantity = 2
        deck_card.asave = AsyncMock()

        mock_deck_cls.objects.aget = AsyncMock(return_value=deck)
        mock_card_cls.objects.aget = AsyncMock(return_value=card)
        mock_deck_card_cls.objects.aget_or_create = AsyncMock(return_value=(deck_card, False))

        deck_total_queryset = MagicMock()
        deck_total_queryset.aaggregate = AsyncMock(return_value={"quantity__sum": 5})
        mock_deck_card_cls.objects.filter.return_value = deck_total_queryset

        task_queryset = MagicMock()
        task_queryset.aupdate = AsyncMock()
        mock_task_cls.objects.filter.return_value = task_queryset

        await add_card_to_deck(_make_ctx(), _CARD_ID, number_to_add=3)

        task_queryset.aupdate.assert_awaited_once_with(deck_size=5)

    @patch(f"{_DECK_TOOLS_MODULE}.DeckBuildTask")
    @patch(f"{_DECK_TOOLS_MODULE}.DeckCard")
    @patch(f"{_DECK_TOOLS_MODULE}.Card")
    @patch(f"{_DECK_TOOLS_MODULE}.Deck")
    async def test_remove_card_updates_deck_size(
        self, mock_deck_cls, mock_card_cls, mock_deck_card_cls, mock_task_cls
    ) -> None:
        """
        GIVEN a valid deck/card and a remove-card operation
        WHEN remove_card_from_deck runs
        THEN DeckBuildTask.deck_size is updated to the remaining total deck size
        """
        deck = MagicMock()
        deck.name = "Test Deck"
        card = MagicMock()
        card.name = "Lightning Bolt"
        deck_card = MagicMock()
        deck_card.quantity = 4
        deck_card.asave = AsyncMock()
        deck_card.adelete = AsyncMock()

        mock_deck_cls.objects.aget = AsyncMock(return_value=deck)
        mock_card_cls.objects.aget = AsyncMock(return_value=card)
        mock_deck_card_cls.objects.aget = AsyncMock(return_value=deck_card)

        deck_total_queryset = MagicMock()
        deck_total_queryset.aaggregate = AsyncMock(return_value={"quantity__sum": 7})
        mock_deck_card_cls.objects.filter.return_value = deck_total_queryset

        task_queryset = MagicMock()
        task_queryset.aupdate = AsyncMock()
        mock_task_cls.objects.filter.return_value = task_queryset

        await remove_card_from_deck(_make_ctx(), _CARD_ID, number_to_remove=1)

        task_queryset.aupdate.assert_awaited_once_with(deck_size=7)

    @patch(f"{_DECK_TOOLS_MODULE}.DeckBuildTask")
    @patch(f"{_DECK_TOOLS_MODULE}.DeckCard")
    @patch(f"{_DECK_TOOLS_MODULE}.Deck")
    async def test_clear_deck_sets_deck_size_to_zero(self, mock_deck_cls, mock_deck_card_cls, mock_task_cls) -> None:
        """
        GIVEN a valid deck clear operation
        WHEN clear_deck runs
        THEN DeckBuildTask.deck_size is reset to zero
        """
        deck = MagicMock()
        deck.name = "Test Deck"
        mock_deck_cls.objects.aget = AsyncMock(return_value=deck)

        delete_queryset = MagicMock()
        delete_queryset.adelete = AsyncMock()
        mock_deck_card_cls.objects.filter.return_value = delete_queryset

        task_queryset = MagicMock()
        task_queryset.aupdate = AsyncMock()
        mock_task_cls.objects.filter.return_value = task_queryset

        await clear_deck(_make_ctx())

        task_queryset.aupdate.assert_awaited_once_with(deck_size=0)


class QueryToolSearchCountUpdateTests(TestCase):
    """Tests for search tool updates to DeckBuildTask.n_searches."""

    @patch(f"{_QUERY_TOOLS_MODULE}.CardSearchResults", side_effect=lambda **kwargs: SimpleNamespace(**kwargs))
    @patch(f"{_QUERY_TOOLS_MODULE}.DeckBuildTask")
    @patch(f"{_QUERY_TOOLS_MODULE}.Card")
    @patch(f"{_QUERY_TOOLS_MODULE}.card_to_info", return_value={"id": str(_CARD_ID)})
    @patch(f"{_QUERY_TOOLS_MODULE}.run_query_from_dsl")
    @patch(f"{_QUERY_TOOLS_MODULE}.sync_to_async", side_effect=_immediate_sync_to_async)
    async def test_search_for_cards_increments_search_count(
        self,
        _mock_sync_to_async,
        mock_run_query,
        _mock_card_to_info,
        mock_card_cls,
        mock_task_cls,
        _mock_search_results,
    ) -> None:
        """
        GIVEN a card search request in deck building
        WHEN search_for_cards runs
        THEN DeckBuildTask.n_searches is incremented with an F-expression update
        """
        existing_card_id = UUID("dddddddd-dddd-dddd-dddd-dddddddddddd")
        existing_cards_queryset = MagicMock()
        existing_cards_queryset.values_list.return_value = [existing_card_id]
        with patch(f"{_QUERY_TOOLS_MODULE}.DeckCard") as mock_deck_card_cls:
            mock_deck_card_cls.objects.filter.return_value = existing_cards_queryset

            mock_run_query.return_value = [SimpleNamespace(id=_CARD_ID)]
            mock_card_cls.objects.aget = AsyncMock(return_value=MagicMock())

            task_queryset = MagicMock()
            task_queryset.aupdate = AsyncMock()
            mock_task_cls.objects.filter.return_value = task_queryset

            await search_for_cards(
                _make_ctx(),
                card_description="Cheap red burn spell for aggressive strategy.",
                search_with_advanced_filter=False,
                max_results=10,
            )

        update_expr = task_queryset.aupdate.await_args.kwargs["n_searches"]
        self.assertEqual(update_expr.lhs.name, "n_searches")
        self.assertEqual(update_expr.rhs.value, 1)
