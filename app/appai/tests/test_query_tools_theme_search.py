from __future__ import annotations

from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from appcards.constants.storage import THEME_COLLECTION_NAME
from django.test import TestCase

from appai.services.agents.tools.query_tools import NewTheme, find_similar_themes

_MODULE = "appai.services.agents.tools.query_tools"


def _immediate_sync_to_async(func):
    async def _runner(*args, **kwargs):
        return func(*args, **kwargs)

    return _runner


class SearchForThemesToolTests(TestCase):
    """Tests for search_for_themes tool behavior."""

    @patch(f"{_MODULE}.sync_to_async", side_effect=_immediate_sync_to_async)
    @patch(f"{_MODULE}.run_query_from_dsl")
    async def test_filters_invalid_results_and_calculates_days_since(
        self,
        mock_run_query,
        _mock_sync_to_async,
    ):
        """
        GIVEN a mix of valid/invalid vector search points
        WHEN search_for_themes is called
        THEN only valid points above score threshold are returned with computed days_since
        """
        three_days_ago = (datetime.now() - timedelta(days=3)).date().isoformat()
        mock_run_query.return_value = [
            SimpleNamespace(score=0.20, payload={"description": "Too low", "date": three_days_ago}),
            SimpleNamespace(score=0.90, payload=None),
            SimpleNamespace(score=0.90, payload={"description": "Missing date"}),
            SimpleNamespace(
                score=0.90,
                payload={"description": "Artifacts in graveyard matter.", "date": three_days_ago},
            ),
        ]

        result = await find_similar_themes(
            ctx=MagicMock(),
            proposed_theme=NewTheme(description="Artifacts are recurred from graveyard for value."),
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].description, "Artifacts in graveyard matter.")
        self.assertEqual(result[0].days_since, 3)

    @patch(f"{_MODULE}.sync_to_async", side_effect=_immediate_sync_to_async)
    @patch(f"{_MODULE}.run_query_from_dsl", return_value=[])
    async def test_uses_theme_collection_and_limit_five(self, mock_run_query, _mock_sync_to_async):
        """
        GIVEN a theme query
        WHEN search_for_themes is called
        THEN it runs the search against the theme collection with limit=5 and no filter
        """
        await find_similar_themes(
            ctx=MagicMock(),
            proposed_theme=NewTheme(description="Token go-wide strategy with anthem effects."),
        )

        mock_run_query.assert_called_once()
        query_arg = mock_run_query.call_args.args[0]

        self.assertEqual(query_arg.collection_name, THEME_COLLECTION_NAME)
        self.assertEqual(query_arg.query_string, "Token go-wide strategy with anthem effects.")
        self.assertIsNone(query_arg.filter)
        self.assertEqual(query_arg.limit, 5)
