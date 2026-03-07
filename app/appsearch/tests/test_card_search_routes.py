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

from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import UUID

from appcards.models.card import ManaColorEnum, Rarity, TypeEnum
from appcards.modules.card_info import CardInfo
from django.test import TestCase
from ninja.errors import HttpError

from appsearch.routes.card_search import _check_search_rate_limit, search_cards

_MODULE = "appsearch.routes.card_search"
_CARD_ID_1 = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
_CARD_ID_2 = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")


def _make_card_info(card_id: UUID, name: str) -> CardInfo:
    return CardInfo(
        id=card_id,
        name=name,
        text="sample rules text",
        llm_summary=None,
        tags=[],
        subtypes=[],
        supertypes=[],
        power=None,
        toughness=None,
        mana_cost_red=1,
        mana_cost_blue=0,
        mana_cost_green=0,
        mana_cost_white=0,
        mana_cost_black=0,
        mana_cost_colorless=0,
        converted_mana_cost=1,
        colors=[ManaColorEnum.RED],
        set_codes=["FDN"],
        types=[TypeEnum.CREATURE],
        rarity=Rarity.COMMON,
        keywords=[],
    )


class SearchRateLimitTests(TestCase):
    """Tests for card search rate limiting helper."""

    @patch(f"{_MODULE}.check_auth_rate_limit")
    def test_raises_429_when_rate_limit_exceeded(self, mock_rate_limit):
        """
        GIVEN a denied rate-limit response for card search
        WHEN _check_search_rate_limit is called
        THEN it raises HttpError 429 with retry information
        """
        mock_rate_limit.return_value = SimpleNamespace(allowed=False, retry_after_seconds=17)

        with self.assertRaises(HttpError) as ctx:
            _check_search_rate_limit(MagicMock())

        self.assertEqual(ctx.exception.status_code, 429)
        self.assertIn("Retry in 17s", str(ctx.exception))


class SearchCardsRouteTests(TestCase):
    """Tests for search_cards endpoint."""

    @patch(f"{_MODULE}.card_to_info")
    @patch(f"{_MODULE}.Card")
    @patch(f"{_MODULE}.run_query_from_dsl")
    @patch(f"{_MODULE}._check_search_rate_limit")
    def test_builds_query_and_returns_card_infos(
        self,
        mock_check_rate_limit,
        mock_run_query,
        mock_card,
        mock_card_to_info,
    ):
        """
        GIVEN a valid search payload and found Qdrant points
        WHEN search_cards is called
        THEN it enforces rate limiting, builds DSL query, and returns converted CardInfo list
        """
        payload = SimpleNamespace(
            query="Find aggressive red creatures with haste",
            set_codes=["FDN"],
            colors=[ManaColorEnum.RED],
            tags=["Aggro"],
        )
        mock_run_query.return_value = [SimpleNamespace(id=_CARD_ID_1, score=0.91)]
        card_obj = SimpleNamespace(id=_CARD_ID_1)
        card_info = _make_card_info(_CARD_ID_1, "Test Card")
        mock_card.objects.get.return_value = card_obj
        mock_card_to_info.return_value = card_info

        result = search_cards(MagicMock(), payload)

        mock_check_rate_limit.assert_called_once()
        mock_run_query.assert_called_once()
        dsl_query = mock_run_query.call_args.args[0]
        self.assertEqual(dsl_query.query_string, payload.query)
        self.assertEqual(dsl_query.limit, 25)
        self.assertEqual(dsl_query.collection_name, "cards")
        self.assertEqual(len(dsl_query.filter.must), 3)
        self.assertEqual(dsl_query.filter.must[0].key, "set_codes")
        self.assertEqual(dsl_query.filter.must[0].any, ["FDN"])
        self.assertEqual(dsl_query.filter.must[1].key, "colors")
        self.assertEqual(dsl_query.filter.must[1].any, ["R"])
        self.assertEqual(dsl_query.filter.must[2].key, "tags")
        self.assertEqual(dsl_query.filter.must[2].any, ["Aggro"])
        self.assertEqual(len(result.cards), 1)
        self.assertEqual(result.cards[0].card_info, card_info)
        self.assertEqual(result.cards[0].relevance_score, 0.91)

    @patch(f"{_MODULE}.card_to_info")
    @patch(f"{_MODULE}.Card")
    @patch(f"{_MODULE}.run_query_from_dsl")
    @patch(f"{_MODULE}._check_search_rate_limit")
    def test_skips_points_for_missing_cards(
        self,
        mock_check_rate_limit,
        mock_run_query,
        mock_card,
        mock_card_to_info,
    ):
        """
        GIVEN search points where one referenced card no longer exists
        WHEN search_cards is called
        THEN it skips missing cards and returns info only for existing cards
        """
        payload = SimpleNamespace(
            query="Find aggressive red creatures with haste",
            set_codes=["FDN"],
            colors=[ManaColorEnum.RED],
            tags=["Aggro"],
        )
        mock_run_query.return_value = [
            SimpleNamespace(id=_CARD_ID_1, score=0.14),
            SimpleNamespace(id=_CARD_ID_2, score=0.77),
        ]
        existing_card = SimpleNamespace(id=_CARD_ID_2)
        mock_card.objects.in_bulk.return_value = {_CARD_ID_2: existing_card}
        kept_info = _make_card_info(_CARD_ID_2, "Kept")
        mock_card_to_info.return_value = kept_info

        result = search_cards(MagicMock(), payload)

        mock_check_rate_limit.assert_called_once()
        self.assertEqual(len(result.cards), 1)
        self.assertEqual(result.cards[0].card_info, kept_info)
        self.assertEqual(result.cards[0].relevance_score, 0.77)
        mock_card_to_info.assert_called_once_with(existing_card)
        mock_card.objects.in_bulk.assert_called_once_with([_CARD_ID_1, _CARD_ID_2])
