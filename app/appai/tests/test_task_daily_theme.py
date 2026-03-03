from __future__ import annotations

from datetime import date
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import UUID

from appcards.constants.storage import THEME_COLLECTION_NAME
from django.test import TestCase

from appai.tasks.daily_theme import make_daily_theme

_MODULE = "appai.tasks.daily_theme"


class DailyThemeTaskTests(TestCase):
    """Tests for the make_daily_theme Celery task."""

    @patch(f"{_MODULE}.upsert_documents")
    @patch(f"{_MODULE}.dense_embed")
    @patch(f"{_MODULE}.get_daily_deck_theme")
    @patch(f"{_MODULE}.create_collection_if_not_exists")
    @patch(f"{_MODULE}.DailyDeckTheme")
    def test_returns_early_when_theme_for_today_exists(
        self,
        mock_daily_theme_cls,
        mock_create_collection,
        mock_get_theme,
        mock_dense_embed,
        mock_upsert,
    ):
        """
        GIVEN a DailyDeckTheme already exists for today
        WHEN make_daily_theme runs
        THEN it returns early and does not generate/embed/upsert a new theme
        """
        queryset = MagicMock()
        queryset.exists.return_value = True
        mock_daily_theme_cls.objects.filter.return_value = queryset

        make_daily_theme.run()

        queryset.exists.assert_called_once()
        mock_create_collection.assert_not_called()
        mock_get_theme.assert_not_called()
        mock_dense_embed.assert_not_called()
        mock_upsert.assert_not_called()

    @patch(f"{_MODULE}.qm.PointStruct", side_effect=lambda **kwargs: kwargs)
    @patch(f"{_MODULE}.transaction.atomic")
    @patch(f"{_MODULE}.upsert_documents")
    @patch(f"{_MODULE}.dense_embed")
    @patch(f"{_MODULE}.get_daily_deck_theme")
    @patch(f"{_MODULE}.create_collection_if_not_exists")
    @patch(f"{_MODULE}.DailyDeckTheme")
    def test_generates_theme_embeds_and_upserts(
        self,
        mock_daily_theme_cls,
        mock_create_collection,
        mock_get_theme,
        mock_dense_embed,
        mock_upsert,
        _mock_atomic,
        _mock_point_struct,
    ):
        """
        GIVEN no DailyDeckTheme exists for today
        WHEN make_daily_theme runs successfully
        THEN it generates a theme, stores it, and upserts the matching vector payload
        """
        filter_queryset = MagicMock()
        filter_queryset.exists.return_value = False
        mock_daily_theme_cls.objects.filter.return_value = filter_queryset

        theme_description = "Build around cards that reward sacrificing artifacts for value."
        mock_get_theme.return_value = SimpleNamespace(description=theme_description)
        mock_dense_embed.return_value = [0.01, 0.02, 0.03]

        created_theme = SimpleNamespace(
            id=UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"),
            date=date(2026, 3, 3),
        )
        mock_daily_theme_cls.objects.create.return_value = created_theme

        make_daily_theme.run()

        mock_create_collection.assert_called_once_with(THEME_COLLECTION_NAME)
        mock_get_theme.assert_called_once_with()
        mock_dense_embed.assert_called_once_with(theme_description)
        mock_daily_theme_cls.objects.create.assert_called_once_with(theme=theme_description)

        mock_upsert.assert_called_once()
        upsert_args = mock_upsert.call_args.args
        self.assertEqual(upsert_args[0], THEME_COLLECTION_NAME)
        self.assertEqual(len(upsert_args[1]), 1)
        self.assertEqual(
            upsert_args[1][0],
            {
                "id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
                "vector": [0.01, 0.02, 0.03],
                "payload": {
                    "description": theme_description,
                    "date": "2026-03-03",
                },
            },
        )

    @patch(f"{_MODULE}.dense_embed")
    @patch(f"{_MODULE}.get_daily_deck_theme", side_effect=Exception("boom"))
    @patch(f"{_MODULE}.create_collection_if_not_exists")
    @patch(f"{_MODULE}.DailyDeckTheme")
    def test_raises_runtime_error_when_theme_generation_fails(
        self,
        mock_daily_theme_cls,
        mock_create_collection,
        _mock_get_theme,
        mock_dense_embed,
    ):
        """
        GIVEN an exception is raised while generating the daily theme
        WHEN make_daily_theme runs
        THEN it raises RuntimeError and does not continue to embedding/upsert steps
        """
        filter_queryset = MagicMock()
        filter_queryset.exists.return_value = False
        mock_daily_theme_cls.objects.filter.return_value = filter_queryset

        with self.assertRaises(RuntimeError):
            make_daily_theme.run()

        mock_create_collection.assert_called_once_with(THEME_COLLECTION_NAME)
        mock_dense_embed.assert_not_called()
