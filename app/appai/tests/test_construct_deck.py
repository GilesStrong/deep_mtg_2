from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

from appcards.constants.decks import DECK_CLASSIFICATIONS
from django.test import TestCase
from pydantic import ValidationError

from appai.modules.construct_deck import DeckConstructorResults, construct_deck
from appai.services.agents.deck_constructor import DeckConstructionOutput

_MODULE = "appai.modules.construct_deck"

_USER_ID = UUID("12345678-1234-5678-1234-567812345678")
_DECK_ID = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
_DECK_DESCRIPTION = "A aggressive red deck focused on burn spells"


def _make_agent_response(summary="A great deck", short_summary="Burn deck"):
    response = MagicMock()
    response.summary = summary
    response.short_summary = short_summary
    return response


def _make_deck(deck_id=_DECK_ID, generation_history=None):
    deck = MagicMock()
    deck.id = deck_id
    deck.generation_history = generation_history
    return deck


class ConstructDeckNewDeckTests(TestCase):
    """Tests for construct_deck when no deck_id is provided."""

    @patch(f"{_MODULE}.run_deck_constructor_agent")
    @patch(f"{_MODULE}.Deck")
    async def test_creates_new_deck_when_no_deck_id(self, mock_deck_cls, mock_agent):
        """
        GIVEN no deck_id is provided
        WHEN construct_deck is called
        THEN a new deck is created via Deck.objects.acreate with name='New Deck'
        """
        new_deck = _make_deck(generation_history=None)
        mock_deck_cls.objects.acreate = AsyncMock(return_value=new_deck)
        mock_agent.return_value = _make_agent_response()

        await construct_deck(deck_description=_DECK_DESCRIPTION, user_id=_USER_ID)

        mock_deck_cls.objects.acreate.assert_called_once_with(name="New Deck", user_id=_USER_ID)

    @patch(f"{_MODULE}.run_deck_constructor_agent")
    @patch(f"{_MODULE}.Deck")
    async def test_does_not_fetch_existing_deck_when_no_deck_id(self, mock_deck_cls, mock_agent):
        """
        GIVEN no deck_id is provided
        WHEN construct_deck is called
        THEN Deck.objects.aget is never called
        """
        new_deck = _make_deck(generation_history=None)
        mock_deck_cls.objects.acreate = AsyncMock(return_value=new_deck)
        mock_agent.return_value = _make_agent_response()

        await construct_deck(deck_description=_DECK_DESCRIPTION, user_id=_USER_ID)

        mock_deck_cls.objects.aget.assert_not_called()

    @patch(f"{_MODULE}.run_deck_constructor_agent")
    @patch(f"{_MODULE}.Deck")
    async def test_returns_correct_deck_id_for_new_deck(self, mock_deck_cls, mock_agent):
        """
        GIVEN no deck_id is provided and a new deck is created
        WHEN construct_deck is called
        THEN the returned DeckConstructorResults.deck_id matches the new deck's ID
        """
        new_deck = _make_deck(deck_id=_DECK_ID, generation_history=None)
        mock_deck_cls.objects.acreate = AsyncMock(return_value=new_deck)
        mock_agent.return_value = _make_agent_response()

        result = await construct_deck(deck_description=_DECK_DESCRIPTION, user_id=_USER_ID)

        self.assertEqual(result.deck_id, _DECK_ID)


class ConstructDeckExistingDeckTests(TestCase):
    """Tests for construct_deck when a deck_id is provided."""

    @patch(f"{_MODULE}.run_deck_constructor_agent")
    @patch(f"{_MODULE}.Deck")
    async def test_fetches_existing_deck_by_id(self, mock_deck_cls, mock_agent):
        """
        GIVEN a valid deck_id is provided
        WHEN construct_deck is called
        THEN the existing deck is fetched via Deck.objects.aget with that ID
        """
        existing_deck = _make_deck(generation_history=[])
        mock_deck_cls.objects.aget = AsyncMock(return_value=existing_deck)
        mock_agent.return_value = _make_agent_response()

        await construct_deck(deck_description=_DECK_DESCRIPTION, user_id=_USER_ID, deck_id=_DECK_ID)

        mock_deck_cls.objects.aget.assert_called_once_with(id=_DECK_ID)

    @patch(f"{_MODULE}.run_deck_constructor_agent")
    @patch(f"{_MODULE}.Deck")
    async def test_does_not_create_deck_when_deck_id_provided(self, mock_deck_cls, mock_agent):
        """
        GIVEN a valid deck_id is provided
        WHEN construct_deck is called
        THEN Deck.objects.acreate is never called
        """
        existing_deck = _make_deck(generation_history=[])
        mock_deck_cls.objects.aget = AsyncMock(return_value=existing_deck)
        mock_agent.return_value = _make_agent_response()

        await construct_deck(deck_description=_DECK_DESCRIPTION, user_id=_USER_ID, deck_id=_DECK_ID)

        mock_deck_cls.objects.acreate.assert_not_called()

    @patch(f"{_MODULE}.run_deck_constructor_agent")
    @patch(f"{_MODULE}.Deck")
    async def test_returns_correct_deck_id_for_existing_deck(self, mock_deck_cls, mock_agent):
        """
        GIVEN a valid deck_id is provided and the deck is fetched
        WHEN construct_deck is called
        THEN the returned DeckConstructorResults.deck_id matches the fetched deck's ID
        """
        existing_deck = _make_deck(deck_id=_DECK_ID, generation_history=[])
        mock_deck_cls.objects.aget = AsyncMock(return_value=existing_deck)
        mock_agent.return_value = _make_agent_response()

        result = await construct_deck(deck_description=_DECK_DESCRIPTION, user_id=_USER_ID, deck_id=_DECK_ID)

        self.assertEqual(result.deck_id, _DECK_ID)


class ConstructDeckGenerationHistoryTests(TestCase):
    """Tests for generation history handling in construct_deck."""

    @patch(f"{_MODULE}.run_deck_constructor_agent")
    @patch(f"{_MODULE}.Deck")
    async def test_none_generation_history_passed_as_empty_list(self, mock_deck_cls, mock_agent):
        """
        GIVEN a deck with generation_history of None
        WHEN construct_deck is called
        THEN the agent is called with an empty list for generation_history
        """
        deck = _make_deck(generation_history=None)
        mock_deck_cls.objects.acreate = AsyncMock(return_value=deck)
        mock_agent.return_value = _make_agent_response()

        await construct_deck(deck_description=_DECK_DESCRIPTION, user_id=_USER_ID)

        mock_agent.assert_called_once()
        call_kwargs = mock_agent.call_args.kwargs
        self.assertEqual(call_kwargs["generation_history"], [])

    @patch(f"{_MODULE}.run_deck_constructor_agent")
    @patch(f"{_MODULE}.Deck")
    async def test_short_history_passed_unchanged(self, mock_deck_cls, mock_agent):
        """
        GIVEN a deck with 3 generation history entries (within the 5-entry cap)
        WHEN construct_deck is called
        THEN the agent receives all 3 entries unchanged
        """
        history = ["h1", "h2", "h3"]
        deck = _make_deck(generation_history=history)
        mock_deck_cls.objects.acreate = AsyncMock(return_value=deck)
        mock_agent.return_value = _make_agent_response()

        await construct_deck(deck_description=_DECK_DESCRIPTION, user_id=_USER_ID)

        call_kwargs = mock_agent.call_args.kwargs
        self.assertEqual(call_kwargs["generation_history"], history)

    @patch(f"{_MODULE}.run_deck_constructor_agent")
    @patch(f"{_MODULE}.Deck")
    async def test_history_exactly_five_passed_unchanged(self, mock_deck_cls, mock_agent):
        """
        GIVEN a deck with exactly 5 generation history entries (at the cap boundary)
        WHEN construct_deck is called
        THEN the agent receives all 5 entries unchanged
        """
        history = ["h1", "h2", "h3", "h4", "h5"]
        deck = _make_deck(generation_history=history)
        mock_deck_cls.objects.acreate = AsyncMock(return_value=deck)
        mock_agent.return_value = _make_agent_response()

        await construct_deck(deck_description=_DECK_DESCRIPTION, user_id=_USER_ID)

        call_kwargs = mock_agent.call_args.kwargs
        self.assertEqual(call_kwargs["generation_history"], history)

    @patch(f"{_MODULE}.run_deck_constructor_agent")
    @patch(f"{_MODULE}.Deck")
    async def test_history_over_five_is_trimmed(self, mock_deck_cls, mock_agent):
        """
        GIVEN a deck with 7 generation history entries (exceeding the 5-entry cap)
        WHEN construct_deck is called
        THEN the agent receives 5 entries: the first entry plus the 4 most recent
        """
        history = ["h1", "h2", "h3", "h4", "h5", "h6", "h7"]
        deck = _make_deck(generation_history=history)
        mock_deck_cls.objects.acreate = AsyncMock(return_value=deck)
        mock_agent.return_value = _make_agent_response()

        await construct_deck(deck_description=_DECK_DESCRIPTION, user_id=_USER_ID)

        call_kwargs = mock_agent.call_args.kwargs
        self.assertEqual(call_kwargs["generation_history"], ["h1", "h4", "h5", "h6", "h7"])

    @patch(f"{_MODULE}.run_deck_constructor_agent")
    @patch(f"{_MODULE}.Deck")
    async def test_history_trimmed_always_keeps_first_entry(self, mock_deck_cls, mock_agent):
        """
        GIVEN a deck with 10 generation history entries
        WHEN construct_deck is called
        THEN the trimmed history always retains the first entry as its first element
        """
        history = [f"h{i}" for i in range(1, 11)]  # h1..h10
        deck = _make_deck(generation_history=history)
        mock_deck_cls.objects.acreate = AsyncMock(return_value=deck)
        mock_agent.return_value = _make_agent_response()

        await construct_deck(deck_description=_DECK_DESCRIPTION, user_id=_USER_ID)

        call_kwargs = mock_agent.call_args.kwargs
        trimmed = call_kwargs["generation_history"]
        self.assertEqual(trimmed[0], "h1")
        self.assertEqual(len(trimmed), 5)
        self.assertEqual(trimmed[1:], ["h7", "h8", "h9", "h10"])


class ConstructDeckReturnValueTests(TestCase):
    """Tests for the return value of construct_deck."""

    @patch(f"{_MODULE}.run_deck_constructor_agent")
    @patch(f"{_MODULE}.Deck")
    async def test_returns_deck_constructor_results_instance(self, mock_deck_cls, mock_agent):
        """
        GIVEN a successful agent run
        WHEN construct_deck is called
        THEN the return value is an instance of DeckConstructorResults
        """
        deck = _make_deck(generation_history=None)
        mock_deck_cls.objects.acreate = AsyncMock(return_value=deck)
        mock_agent.return_value = _make_agent_response()

        result = await construct_deck(deck_description=_DECK_DESCRIPTION, user_id=_USER_ID)

        self.assertIsInstance(result, DeckConstructorResults)

    @patch(f"{_MODULE}.run_deck_constructor_agent")
    @patch(f"{_MODULE}.Deck")
    async def test_deck_summary_mapped_from_agent_response(self, mock_deck_cls, mock_agent):
        """
        GIVEN an agent response with a specific summary
        WHEN construct_deck is called
        THEN the returned deck_summary matches the agent's response.summary
        """
        deck = _make_deck(generation_history=None)
        mock_deck_cls.objects.acreate = AsyncMock(return_value=deck)
        mock_agent.return_value = _make_agent_response(summary="Detailed deck summary")

        result = await construct_deck(deck_description=_DECK_DESCRIPTION, user_id=_USER_ID)

        self.assertEqual(result.deck_summary, "Detailed deck summary")

    @patch(f"{_MODULE}.run_deck_constructor_agent")
    @patch(f"{_MODULE}.Deck")
    async def test_deck_short_summary_mapped_from_agent_response(self, mock_deck_cls, mock_agent):
        """
        GIVEN an agent response with a specific short_summary
        WHEN construct_deck is called
        THEN the returned deck_short_summary matches the agent's response.short_summary
        """
        deck = _make_deck(generation_history=None)
        mock_deck_cls.objects.acreate = AsyncMock(return_value=deck)
        mock_agent.return_value = _make_agent_response(short_summary="Short blurb")

        result = await construct_deck(deck_description=_DECK_DESCRIPTION, user_id=_USER_ID)

        self.assertEqual(result.deck_short_summary, "Short blurb")

    @patch(f"{_MODULE}.run_deck_constructor_agent")
    @patch(f"{_MODULE}.Deck")
    async def test_agent_called_with_correct_deck_description(self, mock_deck_cls, mock_agent):
        """
        GIVEN a specific deck description
        WHEN construct_deck is called
        THEN the agent is invoked with that same deck_description
        """
        deck = _make_deck(generation_history=None)
        mock_deck_cls.objects.acreate = AsyncMock(return_value=deck)
        mock_agent.return_value = _make_agent_response()

        await construct_deck(deck_description=_DECK_DESCRIPTION, user_id=_USER_ID)

        call_kwargs = mock_agent.call_args.kwargs
        self.assertEqual(call_kwargs["deck_description"], _DECK_DESCRIPTION)

    @patch(f"{_MODULE}.run_deck_constructor_agent")
    @patch(f"{_MODULE}.Deck")
    async def test_agent_called_with_available_set_codes(self, mock_deck_cls, mock_agent):
        """
        GIVEN a set of available_set_codes is provided
        WHEN construct_deck is called
        THEN the agent is invoked with those same set codes
        """
        deck = _make_deck(generation_history=None)
        mock_deck_cls.objects.acreate = AsyncMock(return_value=deck)
        mock_agent.return_value = _make_agent_response()
        set_codes = {"MOM", "ONE", "BRO"}

        await construct_deck(deck_description=_DECK_DESCRIPTION, user_id=_USER_ID, available_set_codes=set_codes)

        call_kwargs = mock_agent.call_args.kwargs
        self.assertEqual(call_kwargs["available_set_codes"], set_codes)


class DeckConstructionOutputTagsTests(TestCase):
    """Tests for DeckConstructionOutput tags validation."""

    def test_accepts_and_deduplicates_valid_tags(self):
        """
        GIVEN DeckConstructionOutput with valid duplicate tags
        WHEN the model is created
        THEN tags are deduplicated and remain valid deck classification tags
        """
        valid_tags = list(DECK_CLASSIFICATIONS.keys())
        self.assertGreaterEqual(len(valid_tags), 2)

        output = DeckConstructionOutput(
            deck_name="Mono Red",
            summary="A" * 60,
            short_summary="A" * 15,
            tags=[valid_tags[0], valid_tags[0], valid_tags[1]],
        )

        self.assertCountEqual(output.tags, [valid_tags[0], valid_tags[1]])

    def test_rejects_invalid_tags(self):
        """
        GIVEN DeckConstructionOutput with an invalid tag value
        WHEN the model is created
        THEN pydantic raises a validation error for invalid tags
        """
        with self.assertRaises(ValidationError) as ctx:
            DeckConstructionOutput(
                deck_name="Mono Red",
                summary="A" * 60,
                short_summary="A" * 15,
                tags=["not-a-real-tag"],
            )

        self.assertIn("Invalid tags", str(ctx.exception))
