from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

from django.test import TestCase

from appai.modules.construct_deck import construct_deck

_MODULE = "appai.modules.construct_deck"

_USER_ID = UUID("12345678-1234-5678-1234-567812345678")
_DECK_ID = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
_BUILD_TASK_ID = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
_DECK_DESCRIPTION = "A aggressive red deck focused on burn spells"


def _make_deck(deck_id=_DECK_ID, generation_history=None):
    deck = MagicMock()
    deck.id = deck_id
    deck.generation_history = generation_history
    return deck


class ConstructDeckNewDeckTests(TestCase):
    """Tests for construct_deck when no deck_id is provided."""

    @patch(f"{_MODULE}.construct_deck_graph", new_callable=AsyncMock)
    @patch(f"{_MODULE}.Deck")
    async def test_creates_new_deck_when_no_deck_id(self, mock_deck_cls, mock_graph):
        """
        GIVEN no deck_id is provided
        WHEN construct_deck is called
        THEN a new deck is created via Deck.objects.acreate with name='New Deck'
        """
        new_deck = _make_deck(generation_history=None)
        mock_deck_cls.objects.acreate = AsyncMock(return_value=new_deck)

        await construct_deck(deck_description=_DECK_DESCRIPTION, user_id=_USER_ID, build_task_id=_BUILD_TASK_ID)

        mock_deck_cls.objects.acreate.assert_called_once_with(name="New Deck", user_id=_USER_ID)
        mock_graph.assert_awaited_once()

    @patch(f"{_MODULE}.construct_deck_graph", new_callable=AsyncMock)
    @patch(f"{_MODULE}.Deck")
    async def test_does_not_fetch_existing_deck_when_no_deck_id(self, mock_deck_cls, _mock_graph):
        """
        GIVEN no deck_id is provided
        WHEN construct_deck is called
        THEN Deck.objects.aget is never called
        """
        new_deck = _make_deck(generation_history=None)
        mock_deck_cls.objects.acreate = AsyncMock(return_value=new_deck)

        await construct_deck(deck_description=_DECK_DESCRIPTION, user_id=_USER_ID, build_task_id=_BUILD_TASK_ID)

        mock_deck_cls.objects.aget.assert_not_called()

    @patch(f"{_MODULE}.construct_deck_graph", new_callable=AsyncMock)
    @patch(f"{_MODULE}.Deck")
    async def test_returns_none_for_new_deck(self, mock_deck_cls, _mock_graph):
        """
        GIVEN no deck_id is provided
        WHEN construct_deck is called
        THEN the function returns None
        """
        new_deck = _make_deck(deck_id=_DECK_ID, generation_history=None)
        mock_deck_cls.objects.acreate = AsyncMock(return_value=new_deck)

        result = await construct_deck(
            deck_description=_DECK_DESCRIPTION, user_id=_USER_ID, build_task_id=_BUILD_TASK_ID
        )

        self.assertIsNone(result)


class ConstructDeckExistingDeckTests(TestCase):
    """Tests for construct_deck when a deck_id is provided."""

    @patch(f"{_MODULE}.construct_deck_graph", new_callable=AsyncMock)
    @patch(f"{_MODULE}.Deck")
    async def test_fetches_existing_deck_by_id(self, mock_deck_cls, _mock_graph):
        """
        GIVEN a valid deck_id is provided
        WHEN construct_deck is called
        THEN the existing deck is fetched via Deck.objects.aget with that ID
        """
        existing_deck = _make_deck(generation_history=[])
        mock_deck_cls.objects.aget = AsyncMock(return_value=existing_deck)

        await construct_deck(
            deck_description=_DECK_DESCRIPTION,
            user_id=_USER_ID,
            deck_id=_DECK_ID,
            build_task_id=_BUILD_TASK_ID,
        )

        mock_deck_cls.objects.aget.assert_called_once_with(id=_DECK_ID)

    @patch(f"{_MODULE}.construct_deck_graph", new_callable=AsyncMock)
    @patch(f"{_MODULE}.Deck")
    async def test_does_not_create_deck_when_deck_id_provided(self, mock_deck_cls, _mock_graph):
        """
        GIVEN a valid deck_id is provided
        WHEN construct_deck is called
        THEN Deck.objects.acreate is never called
        """
        existing_deck = _make_deck(generation_history=[])
        mock_deck_cls.objects.aget = AsyncMock(return_value=existing_deck)

        await construct_deck(
            deck_description=_DECK_DESCRIPTION,
            user_id=_USER_ID,
            deck_id=_DECK_ID,
            build_task_id=_BUILD_TASK_ID,
        )

        mock_deck_cls.objects.acreate.assert_not_called()

    @patch(f"{_MODULE}.construct_deck_graph", new_callable=AsyncMock)
    @patch(f"{_MODULE}.Deck")
    async def test_returns_none_for_existing_deck(self, mock_deck_cls, _mock_graph):
        """
        GIVEN a valid deck_id is provided
        WHEN construct_deck is called
        THEN the function returns None
        """
        existing_deck = _make_deck(deck_id=_DECK_ID, generation_history=[])
        mock_deck_cls.objects.aget = AsyncMock(return_value=existing_deck)

        result = await construct_deck(
            deck_description=_DECK_DESCRIPTION,
            user_id=_USER_ID,
            deck_id=_DECK_ID,
            build_task_id=_BUILD_TASK_ID,
        )

        self.assertIsNone(result)


class ConstructDeckGenerationHistoryTests(TestCase):
    """Tests for generation history handling in construct_deck."""

    @patch(f"{_MODULE}.construct_deck_graph", new_callable=AsyncMock)
    @patch(f"{_MODULE}.Deck")
    async def test_none_generation_history_passed_as_empty_list(self, mock_deck_cls, mock_graph):
        """
        GIVEN a deck with generation_history of None
        WHEN construct_deck is called
        THEN the graph is called with an empty list for generation_history
        """
        deck = _make_deck(generation_history=None)
        mock_deck_cls.objects.acreate = AsyncMock(return_value=deck)

        await construct_deck(deck_description=_DECK_DESCRIPTION, user_id=_USER_ID, build_task_id=_BUILD_TASK_ID)

        mock_graph.assert_awaited_once()
        call_kwargs = mock_graph.call_args.kwargs
        self.assertEqual(call_kwargs["generation_history"], [])

    @patch(f"{_MODULE}.construct_deck_graph", new_callable=AsyncMock)
    @patch(f"{_MODULE}.Deck")
    async def test_short_history_passed_unchanged(self, mock_deck_cls, mock_graph):
        """
        GIVEN a deck with 3 generation history entries (within the 5-entry cap)
        WHEN construct_deck is called
        THEN the graph receives all 3 entries unchanged
        """
        history = ["h1", "h2", "h3"]
        deck = _make_deck(generation_history=history)
        mock_deck_cls.objects.acreate = AsyncMock(return_value=deck)

        await construct_deck(deck_description=_DECK_DESCRIPTION, user_id=_USER_ID, build_task_id=_BUILD_TASK_ID)

        call_kwargs = mock_graph.call_args.kwargs
        self.assertEqual(call_kwargs["generation_history"], history)

    @patch(f"{_MODULE}.construct_deck_graph", new_callable=AsyncMock)
    @patch(f"{_MODULE}.Deck")
    async def test_history_exactly_five_passed_unchanged(self, mock_deck_cls, mock_graph):
        """
        GIVEN a deck with exactly 5 generation history entries (at the cap boundary)
        WHEN construct_deck is called
        THEN the graph receives all 5 entries unchanged
        """
        history = ["h1", "h2", "h3", "h4", "h5"]
        deck = _make_deck(generation_history=history)
        mock_deck_cls.objects.acreate = AsyncMock(return_value=deck)

        await construct_deck(deck_description=_DECK_DESCRIPTION, user_id=_USER_ID, build_task_id=_BUILD_TASK_ID)

        call_kwargs = mock_graph.call_args.kwargs
        self.assertEqual(call_kwargs["generation_history"], history)

    @patch(f"{_MODULE}.construct_deck_graph", new_callable=AsyncMock)
    @patch(f"{_MODULE}.Deck")
    async def test_history_over_five_is_trimmed(self, mock_deck_cls, mock_graph):
        """
        GIVEN a deck with 7 generation history entries (exceeding the 5-entry cap)
        WHEN construct_deck is called
        THEN the graph receives 5 entries: the first entry plus the 4 most recent
        """
        history = ["h1", "h2", "h3", "h4", "h5", "h6", "h7"]
        deck = _make_deck(generation_history=history)
        mock_deck_cls.objects.acreate = AsyncMock(return_value=deck)

        await construct_deck(deck_description=_DECK_DESCRIPTION, user_id=_USER_ID, build_task_id=_BUILD_TASK_ID)

        call_kwargs = mock_graph.call_args.kwargs
        self.assertEqual(call_kwargs["generation_history"], ["h1", "h4", "h5", "h6", "h7"])

    @patch(f"{_MODULE}.construct_deck_graph", new_callable=AsyncMock)
    @patch(f"{_MODULE}.Deck")
    async def test_history_trimmed_always_keeps_first_entry(self, mock_deck_cls, mock_graph):
        """
        GIVEN a deck with 10 generation history entries
        WHEN construct_deck is called
        THEN the trimmed history always retains the first entry as its first element
        """
        history = [f"h{i}" for i in range(1, 11)]  # h1..h10
        deck = _make_deck(generation_history=history)
        mock_deck_cls.objects.acreate = AsyncMock(return_value=deck)

        await construct_deck(deck_description=_DECK_DESCRIPTION, user_id=_USER_ID, build_task_id=_BUILD_TASK_ID)

        call_kwargs = mock_graph.call_args.kwargs
        trimmed = call_kwargs["generation_history"]
        self.assertEqual(trimmed[0], "h1")
        self.assertEqual(len(trimmed), 5)
        self.assertEqual(trimmed[1:], ["h7", "h8", "h9", "h10"])


class ConstructDeckGraphCallTests(TestCase):
    """Tests for how construct_deck delegates to the graph layer."""

    @patch(f"{_MODULE}.construct_deck_graph", new_callable=AsyncMock)
    @patch(f"{_MODULE}.Deck")
    async def test_graph_called_with_correct_deck_description(self, mock_deck_cls, mock_graph):
        """
        GIVEN a specific deck description
        WHEN construct_deck is called
        THEN the graph is invoked with that same deck_description
        """
        deck = _make_deck(generation_history=None)
        mock_deck_cls.objects.acreate = AsyncMock(return_value=deck)

        await construct_deck(deck_description=_DECK_DESCRIPTION, user_id=_USER_ID, build_task_id=_BUILD_TASK_ID)

        call_kwargs = mock_graph.call_args.kwargs
        self.assertEqual(call_kwargs["deck_description"], _DECK_DESCRIPTION)

    @patch(f"{_MODULE}.construct_deck_graph", new_callable=AsyncMock)
    @patch(f"{_MODULE}.Deck")
    async def test_graph_called_with_available_set_codes(self, mock_deck_cls, mock_graph):
        """
        GIVEN a set of available_set_codes is provided
        WHEN construct_deck is called
        THEN the graph is invoked with those same set codes
        """
        deck = _make_deck(generation_history=None)
        mock_deck_cls.objects.acreate = AsyncMock(return_value=deck)
        set_codes = {"MOM", "ONE", "BRO"}

        await construct_deck(
            deck_description=_DECK_DESCRIPTION,
            user_id=_USER_ID,
            build_task_id=_BUILD_TASK_ID,
            available_set_codes=set_codes,
        )

        call_kwargs = mock_graph.call_args.kwargs
        self.assertEqual(call_kwargs["available_set_codes"], set_codes)
