from __future__ import annotations

from unittest.mock import patch
from uuid import UUID

from django.test import TestCase
from ninja.errors import HttpError

from appai.serializers.build_deck import BuildDeckPostIn, BuildDeckPostOut, BuildDeckStatusOut

_MODULE = "appai.serializers.build_deck"
_DECK_ID = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
_TASK_ID = UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")


class BuildDeckPostInValidatorTests(TestCase):
    """Tests for BuildDeckPostIn validators."""

    def test_validate_deck_id_none_returns_none(self):
        """
        GIVEN a null deck_id value
        WHEN BuildDeckPostIn.validate_deck_id is called
        THEN it returns None without querying deck existence
        """
        result = BuildDeckPostIn.validate_deck_id(None)
        self.assertIsNone(result)

    @patch(f"{_MODULE}.Deck")
    def test_validate_deck_id_missing_raises_404(self, mock_deck):
        """
        GIVEN a non-null deck_id that does not exist
        WHEN BuildDeckPostIn.validate_deck_id is called
        THEN it raises HttpError with status 404
        """
        mock_deck.objects.filter.return_value.exists.return_value = False

        with self.assertRaises(HttpError) as ctx:
            BuildDeckPostIn.validate_deck_id(_DECK_ID)

        self.assertEqual(ctx.exception.status_code, 404)

    @patch(f"{_MODULE}.Deck")
    def test_validate_deck_id_existing_returns_same_uuid(self, mock_deck):
        """
        GIVEN a non-null deck_id that exists
        WHEN BuildDeckPostIn.validate_deck_id is called
        THEN it returns the same UUID value
        """
        mock_deck.objects.filter.return_value.exists.return_value = True

        result = BuildDeckPostIn.validate_deck_id(_DECK_ID)

        self.assertEqual(result, _DECK_ID)

    def test_validate_set_codes_empty_list_raises_400(self):
        """
        GIVEN an empty set_codes list
        WHEN BuildDeckPostIn.validate_set_codes is called
        THEN it raises HttpError with status 400
        """
        with self.assertRaises(HttpError) as ctx:
            BuildDeckPostIn.validate_set_codes([])

        self.assertEqual(ctx.exception.status_code, 400)

    def test_validate_set_codes_non_empty_returns_value(self):
        """
        GIVEN a non-empty set_codes list
        WHEN BuildDeckPostIn.validate_set_codes is called
        THEN it returns the input list unchanged
        """
        result = BuildDeckPostIn.validate_set_codes(["FDN", "BLB"])
        self.assertEqual(result, ["FDN", "BLB"])


class BuildDeckOutputValidatorTests(TestCase):
    """Tests for BuildDeckPostOut and BuildDeckStatusOut validators."""

    @patch(f"{_MODULE}.Deck")
    def test_post_out_validate_deck_id_missing_raises_runtime_error(self, mock_deck):
        """
        GIVEN a deck_id that does not exist
        WHEN BuildDeckPostOut.validate_deck_id is called
        THEN it raises RuntimeError indicating the deck is missing
        """
        mock_deck.objects.filter.return_value.exists.return_value = False

        with self.assertRaises(RuntimeError):
            BuildDeckPostOut.validate_deck_id(_DECK_ID)

    @patch(f"{_MODULE}.DeckBuildTask")
    def test_post_out_validate_task_id_missing_raises_runtime_error(self, mock_task):
        """
        GIVEN a task_id that does not exist
        WHEN BuildDeckPostOut.validate_task_id is called
        THEN it raises RuntimeError indicating the task is missing
        """
        mock_task.objects.filter.return_value.exists.return_value = False

        with self.assertRaises(RuntimeError):
            BuildDeckPostOut.validate_task_id(_TASK_ID)

    @patch(f"{_MODULE}.Deck")
    def test_status_out_validate_deck_id_existing_returns_uuid(self, mock_deck):
        """
        GIVEN a deck_id that exists
        WHEN BuildDeckStatusOut.validate_deck_id is called
        THEN it returns the same UUID value
        """
        mock_deck.objects.filter.return_value.exists.return_value = True

        result = BuildDeckStatusOut.validate_deck_id(_DECK_ID)

        self.assertEqual(result, _DECK_ID)
