from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import UUID

from appcards.models.card import ManaColorEnum
from django.test import TestCase
from ninja.errors import HttpError

from appsearch.routes.card_search import _check_search_rate_limit, search_cards

_MODULE = "appsearch.routes.card_search"
_CARD_ID_1 = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
_CARD_ID_2 = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")


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
        mock_run_query.return_value = [SimpleNamespace(id=_CARD_ID_1)]
        card_obj = SimpleNamespace(id=_CARD_ID_1)
        card_info = SimpleNamespace(id=_CARD_ID_1, name="Test Card")
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
        self.assertEqual(result, [card_info])

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
        mock_run_query.return_value = [SimpleNamespace(id=_CARD_ID_1), SimpleNamespace(id=_CARD_ID_2)]
        does_not_exist = type("DoesNotExist", (Exception,), {})
        mock_card.DoesNotExist = does_not_exist
        existing_card = SimpleNamespace(id=_CARD_ID_2)
        mock_card.objects.get.side_effect = [does_not_exist(), existing_card]
        kept_info = SimpleNamespace(id=_CARD_ID_2, name="Kept")
        mock_card_to_info.return_value = kept_info

        result = search_cards(MagicMock(), payload)

        mock_check_rate_limit.assert_called_once()
        self.assertEqual(result, [kept_info])
        mock_card_to_info.assert_called_once_with(existing_card)
