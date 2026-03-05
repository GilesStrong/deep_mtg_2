from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

from django.test import TestCase
from pydantic_ai import ModelRetry
from tenacity import stop_after_attempt, wait_exponential

from appai.services.agents.deck_constructor import (
    run_card_classifier_agent,
    run_card_replacement_agent,
    run_deck_constructor_agent,
)

_MODULE = "appai.services.agents.deck_constructor"


def _make_deck_card(name: str, quantity: int = 1) -> MagicMock:
    deck_card = MagicMock()
    deck_card.quantity = quantity
    deck_card.card = SimpleNamespace(
        name=name,
        tags=["tag-a", "tag-b"],
        llm_summary=f"Summary for {name}",
    )
    deck_card.asave = AsyncMock()
    deck_card.role = None
    deck_card.importance = None
    return deck_card


class RunCardClassifierAgentTests(TestCase):
    @patch(f"{_MODULE}.Agent")
    @patch(f"{_MODULE}.DeckCard")
    async def test_classifies_and_persists_roles_and_importance(self, mock_deck_card_cls, mock_agent_cls):
        """
        GIVEN two cards in a deck
        WHEN the classifier agent returns role/importance for both indexed card IDs
        THEN each DeckCard is updated and saved with the expected values
        """
        first = _make_deck_card("First Card", quantity=2)
        second = _make_deck_card("Second Card", quantity=3)
        deck_cards = [first, second]

        queryset = MagicMock()
        queryset.select_related.return_value = deck_cards
        mock_deck_card_cls.objects.filter.return_value = queryset

        classifications = {
            "card_id_00_role": "interaction",
            "card_id_00_importance": "core",
            "card_id_01_role": "wincon",
            "card_id_01_importance": "supporting",
        }
        mock_agent = MagicMock()
        mock_agent.run = AsyncMock(
            return_value=SimpleNamespace(output=SimpleNamespace(model_dump=lambda: classifications))
        )
        mock_agent_cls.return_value = mock_agent

        deck_id = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
        await run_card_classifier_agent(deck_id=deck_id, deck_description="Aggressive spell-based strategy")

        self.assertEqual(first.role, "interaction")
        self.assertEqual(first.importance, "core")
        first.asave.assert_awaited_once_with(update_fields=["role", "importance"])

        self.assertEqual(second.role, "wincon")
        self.assertEqual(second.importance, "supporting")
        second.asave.assert_awaited_once_with(update_fields=["role", "importance"])

        message = mock_agent.run.call_args.args[0]
        self.assertIn("card ID: 00", message)
        self.assertIn("card ID: 01", message)
        self.assertIn("# Deck description", message)

    @patch(f"{_MODULE}.Agent")
    @patch(f"{_MODULE}.DeckCard")
    async def test_skips_save_when_role_or_importance_missing(self, mock_deck_card_cls, mock_agent_cls):
        """
        GIVEN classifier output missing required fields for one card
        WHEN classifications are applied
        THEN only cards with both role and importance are persisted
        """
        first = _make_deck_card("First Card")
        second = _make_deck_card("Second Card")
        deck_cards = [first, second]

        queryset = MagicMock()
        queryset.select_related.return_value = deck_cards
        mock_deck_card_cls.objects.filter.return_value = queryset

        classifications = {
            "card_id_00_role": "interaction",
            "card_id_01_role": "wincon",
            "card_id_01_importance": "core",
        }
        mock_agent = MagicMock()
        mock_agent.run = AsyncMock(
            return_value=SimpleNamespace(output=SimpleNamespace(model_dump=lambda: classifications))
        )
        mock_agent_cls.return_value = mock_agent

        deck_id = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
        await run_card_classifier_agent(deck_id=deck_id, deck_description="Midrange value deck")

        first.asave.assert_not_awaited()
        second.asave.assert_awaited_once_with(update_fields=["role", "importance"])

    @patch(f"{_MODULE}.Agent")
    @patch(f"{_MODULE}.DeckCard")
    async def test_retries_on_transient_agent_error(self, mock_deck_card_cls, mock_agent_cls):
        """
        GIVEN a transient exception during classifier agent execution
        WHEN run_card_classifier_agent is invoked with retry overrides for testing
        THEN the call is retried and card classifications are eventually persisted
        """
        deck_card = _make_deck_card("Retry Card")
        queryset = MagicMock()
        queryset.select_related.return_value = [deck_card]
        mock_deck_card_cls.objects.filter.return_value = queryset

        classifications = {
            "card_id_00_role": "interaction",
            "card_id_00_importance": "core",
        }
        mock_agent = MagicMock()
        mock_agent.run = AsyncMock(
            side_effect=[
                RuntimeError("transient failure"),
                SimpleNamespace(output=SimpleNamespace(model_dump=lambda: classifications)),
            ]
        )
        mock_agent_cls.return_value = mock_agent

        deck_id = UUID("abababab-abab-abab-abab-abababababab")
        await run_card_classifier_agent.retry_with(
            stop=stop_after_attempt(2),
            wait=wait_exponential(multiplier=0, min=0, max=0),
        )(
            deck_id=deck_id,
            deck_description="Resilient tempo deck",
        )

        self.assertEqual(mock_agent.run.await_count, 2)
        deck_card.asave.assert_awaited_once_with(update_fields=["role", "importance"])


class RunDeckConstructorAgentRetryTests(TestCase):
    @patch(f"{_MODULE}.Agent")
    @patch(f"{_MODULE}.Deck")
    async def test_retries_on_transient_agent_error(self, mock_deck_cls, mock_agent_cls):
        """
        GIVEN a transient exception during deck construction agent execution
        WHEN run_deck_constructor_agent is invoked with retry overrides for testing
        THEN the call is retried and deck metadata is persisted from the successful retry
        """
        first_attempt_deck = SimpleNamespace(
            name="New Deck",
            llm_summary=None,
            tags=[],
        )
        second_attempt_deck = SimpleNamespace(
            name="New Deck",
            llm_summary=None,
            tags=[],
        )
        persisted_deck = SimpleNamespace(
            name="New Deck",
            llm_summary=None,
            short_llm_summary=None,
            tags=[],
            generation_history=[],
            asave=AsyncMock(),
        )
        mock_deck_cls.objects.aget = AsyncMock(side_effect=[first_attempt_deck, second_attempt_deck, persisted_deck])

        output = SimpleNamespace(
            deck_name="Izzet Tempo",
            summary="A proactive spells-and-threats deck that pressures early and closes quickly.",
            short_summary="Pressure early with cheap threats and efficient interaction.",
            tags=["Aggro"],
        )
        mock_agent = MagicMock()
        mock_agent.run = AsyncMock(side_effect=[RuntimeError("transient failure"), SimpleNamespace(output=output)])
        mock_agent_cls.return_value = mock_agent

        deck_id = UUID("cdcdcdcd-cdcd-cdcd-cdcd-cdcdcdcdcdcd")
        result = await run_deck_constructor_agent.retry_with(
            stop=stop_after_attempt(2),
            wait=wait_exponential(multiplier=0, min=0, max=0),
        )(
            deck_id=deck_id,
            deck_description="Blue-red tempo with efficient interaction",
            generation_history=[],
            available_set_codes={"FDN"},
        )

        self.assertIs(result, output)
        self.assertEqual(mock_agent.run.await_count, 2)
        self.assertEqual(persisted_deck.name, "Izzet Tempo")
        self.assertEqual(persisted_deck.short_llm_summary, output.short_summary)
        self.assertEqual(persisted_deck.tags, ["Aggro"])
        self.assertEqual(persisted_deck.generation_history, ["Blue-red tempo with efficient interaction"])
        persisted_deck.asave.assert_awaited_once()


class _FakeReplacementAgent:
    next_output: list[UUID] = []
    last_message: str = ""
    last_instance: "_FakeReplacementAgent | None" = None

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self._validator = None
        _FakeReplacementAgent.last_instance = self

    def output_validator(self, fn):
        self._validator = fn
        return fn

    async def run(self, message: str):
        _FakeReplacementAgent.last_message = message
        output = list(_FakeReplacementAgent.next_output)
        if self._validator is not None:
            output = await self._validator(output)
        return SimpleNamespace(output=output)


class RunCardReplacementAgentTests(TestCase):
    @patch(f"{_MODULE}.Agent", new=_FakeReplacementAgent)
    async def test_returns_valid_replacement_ids(self):
        """
        GIVEN candidate replacement cards and valid agent output IDs
        WHEN the replacement agent runs
        THEN it returns those IDs and includes card context in the prompt
        """
        first_id = UUID("11111111-1111-1111-1111-111111111111")
        second_id = UUID("22222222-2222-2222-2222-222222222222")

        card_to_replace = MagicMock()
        card_to_replace.quantity = 2
        card_to_replace.role = "interaction"
        card_to_replace.importance = "core"
        card_to_replace.card = SimpleNamespace(name="Old Card", tags=["instant"], llm_summary="Old summary")

        potential_replacements = [
            SimpleNamespace(id=first_id, name="New Card One", tags=["instant"], llm_summary="One summary"),
            SimpleNamespace(id=second_id, name="New Card Two", tags=["instant"], llm_summary="Two summary"),
        ]

        _FakeReplacementAgent.next_output = [second_id, first_id]

        result = await run_card_replacement_agent(
            deck_strategy="Tempo strategy with efficient interaction",
            card_to_replace=card_to_replace,
            potential_replacements=potential_replacements,
        )

        self.assertEqual(result, [second_id, first_id])
        self.assertIn("# Potential replacements", _FakeReplacementAgent.last_message)
        self.assertIn(str(first_id), _FakeReplacementAgent.last_message)
        self.assertIn(str(second_id), _FakeReplacementAgent.last_message)

    @patch(f"{_MODULE}.Agent", new=_FakeReplacementAgent)
    async def test_raises_model_retry_for_invalid_replacement_id(self):
        """
        GIVEN an agent output containing a card ID not in potential_replacements
        WHEN output validation runs
        THEN ModelRetry is raised
        """
        valid_id = UUID("33333333-3333-3333-3333-333333333333")
        invalid_id = UUID("99999999-9999-9999-9999-999999999999")

        card_to_replace = MagicMock()
        card_to_replace.quantity = 1
        card_to_replace.role = "wincon"
        card_to_replace.importance = "supporting"
        card_to_replace.card = SimpleNamespace(name="Old Card", tags=["creature"], llm_summary="Old summary")

        potential_replacements = [
            SimpleNamespace(id=valid_id, name="Valid Card", tags=["creature"], llm_summary="Valid summary")
        ]

        _FakeReplacementAgent.next_output = [invalid_id]

        with self.assertRaises(ModelRetry):
            await run_card_replacement_agent(
                deck_strategy="Creature-based strategy",
                card_to_replace=card_to_replace,
                potential_replacements=potential_replacements,
            )
