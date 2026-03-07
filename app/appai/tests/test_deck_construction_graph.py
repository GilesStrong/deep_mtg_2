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

import importlib
import sys
import types
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

from django.test import TestCase

_MODULE = "appai.services.graphs.deck_construction"
_BUILD_TASK_ID = UUID("99999999-9999-9999-9999-999999999999")


def _load_deck_construction_module():
    fake_replace_card_module = types.ModuleType("appai.services.graphs.replace_card")
    fake_deck_constructor_module = types.ModuleType("appai.services.agents.deck_constructor")

    async def _fake_replace_card(*args, **kwargs):
        return None

    async def _fake_run_card_classifier_agent(*args, **kwargs):
        return None

    async def _fake_run_deck_constructor_agent(*args, **kwargs):
        return None

    fake_replace_card_module.replace_card = _fake_replace_card
    fake_deck_constructor_module.run_card_classifier_agent = _fake_run_card_classifier_agent
    fake_deck_constructor_module.run_deck_constructor_agent = _fake_run_deck_constructor_agent

    with patch.dict(
        sys.modules,
        {
            "appai.services.graphs.replace_card": fake_replace_card_module,
            "appai.services.agents.deck_constructor": fake_deck_constructor_module,
        },
    ):
        sys.modules.pop(_MODULE, None)
        return importlib.import_module(_MODULE)


def _make_ctx(deck_id: UUID, deck_description: str, build_count: int = 0, generation_history: list[str] | None = None):
    return SimpleNamespace(
        deps=SimpleNamespace(
            deck_id=deck_id,
            deck_description=deck_description,
            available_set_codes={"FDN", "BLB"},
            build_task_id=_BUILD_TASK_ID,
        ),
        state=SimpleNamespace(build_count=build_count, generation_history=generation_history or []),
    )


class BuildDeckNodeTests(TestCase):
    async def test_calls_deck_constructor_and_increments_build_count(self):
        """
        GIVEN a graph context for deck construction
        WHEN BuildDeck.run executes
        THEN it calls run_deck_constructor_agent and increments build_count
        """
        dc = _load_deck_construction_module()
        deck_id = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
        ctx = _make_ctx(deck_id=deck_id, deck_description="Mono-red aggro", build_count=0, generation_history=["g1"])

        mock_run_deck_constructor_agent = AsyncMock()
        with patch.object(dc, "run_deck_constructor_agent", mock_run_deck_constructor_agent):
            result = await dc.BuildDeck().run(ctx)

        self.assertIsInstance(result, dc.ValidateDeck)
        self.assertEqual(ctx.state.build_count, 1)
        mock_run_deck_constructor_agent.assert_awaited_once_with(
            deck_id=deck_id,
            deck_description="Mono-red aggro",
            available_set_codes={"FDN", "BLB"},
            generation_history=["g1"],
        )


class ValidateDeckNodeTests(TestCase):
    async def test_returns_classify_cards_when_deck_is_valid(self):
        """
        GIVEN deck validation passes
        WHEN ValidateDeck.run executes
        THEN it transitions to ClassifyCards
        """
        dc = _load_deck_construction_module()
        mock_deck_cls = MagicMock()
        mock_deck_cls.objects.filter.return_value.aexists = AsyncMock(return_value=True)
        ctx = _make_ctx(
            deck_id=UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"),
            deck_description="Control deck",
            build_count=1,
        )

        with patch.object(dc, "Deck", mock_deck_cls):
            result = await dc.ValidateDeck().run(ctx)

        self.assertIsInstance(result, dc.ClassifyCards)

    async def test_returns_build_deck_when_invalid_and_attempts_remaining(self):
        """
        GIVEN deck validation fails before reaching max attempts
        WHEN ValidateDeck.run executes
        THEN it transitions back to BuildDeck
        """
        dc = _load_deck_construction_module()
        mock_deck_cls = MagicMock()
        mock_deck_cls.objects.filter.return_value.aexists = AsyncMock(return_value=False)
        ctx = _make_ctx(
            deck_id=UUID("cccccccc-cccc-cccc-cccc-cccccccccccc"),
            deck_description="Midrange",
            build_count=1,
        )

        with patch.object(dc, "Deck", mock_deck_cls):
            result = await dc.ValidateDeck().run(ctx)

        self.assertIsInstance(result, dc.BuildDeck)

    async def test_raises_when_invalid_at_max_attempts(self):
        """
        GIVEN deck validation fails at max build attempts
        WHEN ValidateDeck.run executes
        THEN it raises RuntimeError
        """
        dc = _load_deck_construction_module()
        mock_deck_cls = MagicMock()
        mock_deck_cls.objects.filter.return_value.aexists = AsyncMock(return_value=False)
        ctx = _make_ctx(
            deck_id=UUID("dddddddd-dddd-dddd-dddd-dddddddddddd"),
            deck_description="Combo",
            build_count=3,
        )

        with patch.object(dc, "Deck", mock_deck_cls):
            with self.assertRaises(RuntimeError):
                await dc.ValidateDeck().run(ctx)


class ClassifyCardsNodeTests(TestCase):
    async def test_runs_classifier_and_transitions_to_set_swaps(self):
        """
        GIVEN a valid context
        WHEN ClassifyCards.run executes
        THEN it runs card classifier and transitions to SetSwaps
        """
        dc = _load_deck_construction_module()
        deck_id = UUID("eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee")
        ctx = _make_ctx(deck_id=deck_id, deck_description="Tempo")

        mock_run_card_classifier_agent = AsyncMock()
        with patch.object(dc, "run_card_classifier_agent", mock_run_card_classifier_agent):
            result = await dc.ClassifyCards().run(ctx)

        self.assertIsInstance(result, dc.SetSwaps)
        mock_run_card_classifier_agent.assert_awaited_once_with(
            deck_id=deck_id,
            deck_description="Tempo",
        )


class SetSwapsNodeTests(TestCase):
    async def test_replaces_only_non_critical_cards(self):
        """
        GIVEN a deck with a mix of card importances
        WHEN SetSwaps.run executes
        THEN only non-critical/high-synergy cards are sent to replace_card
        """
        dc = _load_deck_construction_module()
        mock_replace_card = AsyncMock()
        mock_get_colors_from_deck = MagicMock(return_value={"R"})
        mock_deck_cls = MagicMock()
        mock_deck_card_cls = MagicMock()

        replace_me = MagicMock()
        replace_me.importance = "Supporting"

        keep_critical = MagicMock()
        keep_critical.importance = "Critical"

        keep_high_synergy = MagicMock()
        keep_high_synergy.importance = "High Synergy"

        first_queryset = MagicMock()
        first_queryset.select_related.return_value = [replace_me, keep_critical, keep_high_synergy]

        existing_card_id = UUID("11111111-1111-1111-1111-111111111111")
        second_queryset = MagicMock()
        second_queryset.values_list.return_value = [existing_card_id]

        mock_deck_card_cls.objects.filter.side_effect = [first_queryset, second_queryset]

        deck = MagicMock()
        deck.llm_summary = None
        mock_deck_cls.objects.aget = AsyncMock(return_value=deck)

        ctx = _make_ctx(
            deck_id=UUID("ffffffff-ffff-ffff-ffff-ffffffffffff"),
            deck_description="Burn strategy",
        )

        with (
            patch.object(dc, "replace_card", mock_replace_card),
            patch.object(dc, "get_colors_from_deck", mock_get_colors_from_deck),
            patch.object(dc, "Deck", mock_deck_cls),
            patch.object(dc, "DeckCard", mock_deck_card_cls),
        ):
            result = await dc.SetSwaps().run(ctx)

        self.assertEqual(result.__class__.__name__, "End")
        mock_replace_card.assert_awaited_once()
        call_kwargs = mock_replace_card.call_args.kwargs
        self.assertEqual(call_kwargs["deck_strategy"], "Burn strategy")
        self.assertIs(call_kwargs["deck_card_to_replace"], replace_me)
        self.assertEqual(call_kwargs["exclude_ids"], [str(existing_card_id)])

    async def test_skips_replacement_when_no_eligible_cards(self):
        """
        GIVEN all deck cards are critical/high-synergy
        WHEN SetSwaps.run executes
        THEN replacement step is skipped
        """
        dc = _load_deck_construction_module()
        mock_replace_card = AsyncMock()
        mock_deck_card_cls = MagicMock()

        critical_card = MagicMock()
        critical_card.importance = "Critical"
        high_synergy_card = MagicMock()
        high_synergy_card.importance = "High Synergy"

        queryset = MagicMock()
        queryset.select_related.return_value = [critical_card, high_synergy_card]
        mock_deck_card_cls.objects.filter.return_value = queryset

        ctx = _make_ctx(
            deck_id=UUID("abababab-abab-abab-abab-abababababab"),
            deck_description="Any strategy",
        )

        with (
            patch.object(dc, "replace_card", mock_replace_card),
            patch.object(dc, "DeckCard", mock_deck_card_cls),
        ):
            result = await dc.SetSwaps().run(ctx)

        self.assertEqual(result.__class__.__name__, "End")
        mock_replace_card.assert_not_awaited()


class ConstructDeckFunctionTests(TestCase):
    async def test_construct_deck_builds_graph_and_runs_with_state(self):
        """
        GIVEN construct_deck is called with explicit set codes
        WHEN orchestration runs
        THEN Graph.run is called with BuildDeck start node plus deps/state
        """
        dc = _load_deck_construction_module()
        mock_deps_cls = MagicMock()
        mock_graph_cls = MagicMock()

        deps_obj = MagicMock()
        mock_deps_cls.return_value = deps_obj

        graph_obj = MagicMock()
        graph_obj.run = AsyncMock()
        mock_graph_cls.return_value = graph_obj

        deck_id = UUID("12121212-1212-1212-1212-121212121212")
        with (
            patch.object(dc, "DeckBuildingDeps", mock_deps_cls),
            patch.object(dc, "Graph", mock_graph_cls),
        ):
            await dc.construct_deck(
                deck_id=deck_id,
                deck_description="Artifacts deck",
                generation_history=["first pass"],
                build_task_id=_BUILD_TASK_ID,
                available_set_codes={"FDN"},
            )

        mock_deps_cls.assert_called_once_with(
            deck_id=deck_id,
            deck_description="Artifacts deck",
            available_set_codes={"FDN"},
            build_task_id=_BUILD_TASK_ID,
        )
        mock_graph_cls.assert_called_once()
        graph_obj.run.assert_awaited_once()

        run_args = graph_obj.run.call_args.args
        run_kwargs = graph_obj.run.call_args.kwargs
        self.assertIsInstance(run_args[0], dc.BuildDeck)
        self.assertIs(run_kwargs["deps"], deps_obj)
        self.assertEqual(run_kwargs["state"].generation_history, ["first pass"])
        self.assertEqual(run_kwargs["state"].build_count, 0)
