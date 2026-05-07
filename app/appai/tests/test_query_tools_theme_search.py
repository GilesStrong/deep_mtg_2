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

from collections.abc import Callable
from datetime import datetime, timedelta
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

from appcards.constants.storage import THEME_COLLECTION_NAME
from django.test import TestCase
from pydantic_ai import ModelRetry

from appai.services.agents.tools.query_tools import NewTheme, find_similar_themes

_MODULE = "appai.services.agents.tools.query_tools"


def _immediate_sync_to_async(func: Callable[..., Any]) -> Callable[..., Any]:
    async def _runner(*args: Any, **kwargs: Any) -> Any:
        return func(*args, **kwargs)

    return _runner


def _build_ctx(*, n_searches: int = 0, n_max_searches: int = 3) -> SimpleNamespace:
    """Build a minimal context object for theme tool calls in tests.

    Args:
        n_searches (int): Number of theme searches already used in this run.
        n_max_searches (int): Maximum number of theme searches allowed in this run.

    Returns:
        SimpleNamespace: Context-like object exposing deps counters used by the tool.
    """
    return SimpleNamespace(deps=SimpleNamespace(n_searches=n_searches, n_max_searches=n_max_searches))


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
        ctx = _build_ctx()

        result = await find_similar_themes(
            ctx=ctx,
            proposed_theme=NewTheme(description="Artifacts are recurred from graveyard for value."),
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].description, "Artifacts in graveyard matter.")
        self.assertEqual(result[0].days_since, 3)
        self.assertEqual(ctx.deps.n_searches, 1)

    @patch(f"{_MODULE}.sync_to_async", side_effect=_immediate_sync_to_async)
    @patch(f"{_MODULE}.run_query_from_dsl", return_value=[])
    async def test_uses_theme_collection_and_limit_five(self, mock_run_query, _mock_sync_to_async):
        """
        GIVEN a theme query
        WHEN search_for_themes is called
        THEN it runs the search against the theme collection with limit=5 and no filter
        """
        ctx = _build_ctx()

        await find_similar_themes(
            ctx=ctx,
            proposed_theme=NewTheme(description="Token go-wide strategy with anthem effects."),
        )

        mock_run_query.assert_called_once()
        query_arg = mock_run_query.call_args.args[0]

        self.assertEqual(query_arg.collection_name, THEME_COLLECTION_NAME)
        self.assertEqual(query_arg.query_string, "Token go-wide strategy with anthem effects.")
        self.assertIsNone(query_arg.filter)
        self.assertEqual(query_arg.limit, 5)
        self.assertEqual(ctx.deps.n_searches, 1)

    @patch(f"{_MODULE}.sync_to_async", side_effect=_immediate_sync_to_async)
    @patch(f"{_MODULE}.run_query_from_dsl")
    async def test_raises_when_search_budget_is_exhausted(self, mock_run_query, _mock_sync_to_async):
        """
        GIVEN the per-run theme search budget is exhausted
        WHEN find_similar_themes is called
        THEN it raises ModelRetry and does not run a vector search
        """
        ctx = _build_ctx(n_searches=3, n_max_searches=3)

        with self.assertRaises(ModelRetry):
            await find_similar_themes(
                ctx=ctx,
                proposed_theme=NewTheme(description="Artifact recursion and sacrifice value engine."),
            )

        self.assertEqual(ctx.deps.n_searches, 3)
        mock_run_query.assert_not_called()
