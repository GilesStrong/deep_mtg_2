from __future__ import annotations

import importlib
import sys
import types
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

from django.test import TestCase

_MODULE = "appai.services.graphs.replace_card"


def _load_replace_card_module():
    fake_agent_module = types.ModuleType("appai.services.agents.deck_constructor")
    fake_qdrant_search_module = types.ModuleType("appsearch.services.qdrant.search")
    fake_deck_model_module = types.ModuleType("appcards.models.deck")

    async def _fake_run_card_classifier_agent(*args, **kwargs):
        return None

    async def _fake_run_card_replacement_agent(*args, **kwargs):
        return []

    async def _fake_run_deck_constructor_agent(*args, **kwargs):
        return None

    def _fake_run_query_from_dsl(*args, **kwargs):
        return []

    class _FakeDeck:
        pass

    fake_agent_module.run_card_classifier_agent = _fake_run_card_classifier_agent
    fake_agent_module.run_card_replacement_agent = _fake_run_card_replacement_agent
    fake_agent_module.run_deck_constructor_agent = _fake_run_deck_constructor_agent

    fake_qdrant_search_module.run_query_from_dsl = _fake_run_query_from_dsl

    fake_deck_model_module.MAX_DECK_NAME_LENGTH = 60
    fake_deck_model_module.SHORT_SUMMARY_LENGTH_LIMIT = (1, 200)
    fake_deck_model_module.SUMMARY_LENGTH_LIMIT = (1, 2000)
    fake_deck_model_module.Deck = _FakeDeck
    fake_deck_model_module.DeckCard = dict

    with patch.dict(
        sys.modules,
        {
            "appai.services.agents.deck_constructor": fake_agent_module,
            "appsearch.services.qdrant.search": fake_qdrant_search_module,
            "appcards.models.deck": fake_deck_model_module,
        },
    ):
        sys.modules.pop(_MODULE, None)
        return importlib.import_module(_MODULE)


class AddReplacementsNodeTests(TestCase):
    async def test_adds_replacement_cards(self):
        """
        GIVEN replacement cards and a deck card
        WHEN AddReplacements.run executes
        THEN replacement cards are refreshed with the provided candidates
        """
        module = _load_replace_card_module()

        replacement_one = MagicMock()
        replacement_two = MagicMock()
        card_to_replace = MagicMock()
        card_to_replace.replacement_cards.aclear = AsyncMock()
        card_to_replace.replacement_cards.aadd = AsyncMock()

        ctx = SimpleNamespace(deps=SimpleNamespace(card_to_replace=card_to_replace))
        result = await module.AddReplacements(replacement_cards=[replacement_one, replacement_two]).run(ctx)

        self.assertEqual(result.__class__.__name__, "End")
        card_to_replace.replacement_cards.aclear.assert_awaited_once_with()
        card_to_replace.replacement_cards.aadd.assert_awaited_once_with(replacement_one, replacement_two)


class FilterReplacementsNodeTests(TestCase):
    async def test_returns_end_when_no_filtered_candidates(self):
        """
        GIVEN replacement candidates but agent returns no valid IDs
        WHEN FilterReplacements.run executes
        THEN graph terminates with End
        """
        module = _load_replace_card_module()

        candidate_id = UUID("11111111-1111-1111-1111-111111111111")
        candidate = SimpleNamespace(id=candidate_id, name="Candidate")
        card_to_replace = SimpleNamespace(card=SimpleNamespace(name="Target"))
        ctx = SimpleNamespace(deps=SimpleNamespace(deck_strategy="Control", card_to_replace=card_to_replace))

        with patch.object(module, "run_card_replacement_agent", AsyncMock(return_value=[])):
            result = await module.FilterReplacements(replacement_candidates=[candidate]).run(ctx)

        self.assertEqual(result.__class__.__name__, "End")

    async def test_returns_add_replacements_with_filtered_cards(self):
        """
        GIVEN replacement candidates and valid filtered candidate IDs
        WHEN FilterReplacements.run executes
        THEN it transitions to AddReplacements with matching cards only
        """
        module = _load_replace_card_module()

        first_id = UUID("22222222-2222-2222-2222-222222222222")
        second_id = UUID("33333333-3333-3333-3333-333333333333")
        first = SimpleNamespace(id=first_id, name="First")
        second = SimpleNamespace(id=second_id, name="Second")

        card_to_replace = SimpleNamespace(card=SimpleNamespace(name="Target"))
        ctx = SimpleNamespace(deps=SimpleNamespace(deck_strategy="Tempo", card_to_replace=card_to_replace))

        with patch.object(module, "run_card_replacement_agent", AsyncMock(return_value=[second_id])):
            result = await module.FilterReplacements(replacement_candidates=[first, second]).run(ctx)

        self.assertIsInstance(result, module.AddReplacements)
        self.assertEqual(result.replacement_cards, [second])


class SearchForReplacementsNodeTests(TestCase):
    async def test_returns_end_when_no_candidates_found(self):
        """
        GIVEN vector search returns no card points
        WHEN SearchForReplacements.run executes
        THEN graph terminates with End
        """
        module = _load_replace_card_module()

        run_query_mock = MagicMock(return_value=[])
        card_mock = MagicMock()
        card_mock.objects.aget = AsyncMock()

        card_to_replace = SimpleNamespace(card=SimpleNamespace(llm_summary="summary", name="Target"))
        ctx = SimpleNamespace(deps=SimpleNamespace(card_to_replace=card_to_replace))

        with (
            patch.object(module, "run_query_from_dsl", run_query_mock),
            patch.object(module, "Card", card_mock),
        ):
            result = await module.SearchForReplacements(card_filter=module.Filter(must=[]), exclude_ids=["a"]).run(ctx)

        self.assertEqual(result.__class__.__name__, "End")
        run_query_mock.assert_called_once()
        card_mock.objects.aget.assert_not_awaited()

    async def test_returns_filter_replacements_for_resolved_cards(self):
        """
        GIVEN vector search returns points and some resolve to cards
        WHEN SearchForReplacements.run executes
        THEN it transitions to FilterReplacements with resolved cards only
        """
        module = _load_replace_card_module()

        first_id = UUID("44444444-4444-4444-4444-444444444444")
        second_id = UUID("55555555-5555-5555-5555-555555555555")
        points = [SimpleNamespace(id=first_id), SimpleNamespace(id=second_id)]
        run_query_mock = MagicMock(return_value=points)

        card_one = MagicMock()

        class _DoesNotExist(Exception):
            pass

        card_mock = MagicMock()
        card_mock.DoesNotExist = _DoesNotExist
        card_mock.objects.aget = AsyncMock(side_effect=[card_one, _DoesNotExist()])

        card_to_replace = SimpleNamespace(card=SimpleNamespace(llm_summary="summary", name="Target"))
        ctx = SimpleNamespace(deps=SimpleNamespace(card_to_replace=card_to_replace))

        with (
            patch.object(module, "run_query_from_dsl", run_query_mock),
            patch.object(module, "Card", card_mock),
        ):
            result = await module.SearchForReplacements(card_filter=module.Filter(must=[]), exclude_ids=["x"]).run(ctx)

        self.assertIsInstance(result, module.FilterReplacements)
        self.assertEqual(result.replacement_candidates, [card_one])


class ReplaceCardOrchestrationTests(TestCase):
    async def test_builds_graph_and_runs_with_search_node_and_deps(self):
        """
        GIVEN replace_card inputs
        WHEN replace_card executes
        THEN it constructs the graph and starts from SearchForReplacements with expected deps
        """
        module = _load_replace_card_module()

        graph_obj = MagicMock()
        graph_obj.run = AsyncMock()
        graph_cls = MagicMock(return_value=graph_obj)

        card_to_replace = {}
        card_filter = MagicMock()

        with patch.object(module, "Graph", graph_cls):
            await module.replace_card(
                deck_strategy="Spellslinger",
                deck_card_to_replace=card_to_replace,
                card_filter=card_filter,
                exclude_ids=["id-1", "id-2"],
            )

        graph_cls.assert_called_once()
        graph_kwargs = graph_cls.call_args.kwargs
        self.assertEqual(
            graph_kwargs["nodes"],
            [module.SearchForReplacements, module.FilterReplacements, module.AddReplacements],
        )

        graph_obj.run.assert_awaited_once()
        run_args = graph_obj.run.call_args.args
        run_kwargs = graph_obj.run.call_args.kwargs
        self.assertIsInstance(run_args[0], module.SearchForReplacements)
        self.assertEqual(run_args[0].card_filter, card_filter)
        self.assertEqual(run_args[0].exclude_ids, ["id-1", "id-2"])
        self.assertEqual(run_kwargs["deps"].deck_strategy, "Spellslinger")
        self.assertEqual(run_kwargs["deps"].card_to_replace, card_to_replace)
