from __future__ import annotations

from django.test import TestCase
from ninja.errors import HttpError

from appsearch.serializers.card_search import SearchCardsIn


class SearchCardsInValidatorTests(TestCase):
    """Tests for SearchCardsIn validators."""

    def test_validate_tags_rejects_non_list(self):
        """
        GIVEN tags provided as a non-list value
        WHEN SearchCardsIn.validate_tags is called
        THEN it raises ValueError indicating tags must be a list
        """
        with self.assertRaises(ValueError):
            SearchCardsIn.validate_tags("Aggro")

    def test_validate_tags_rejects_invalid_tags(self):
        """
        GIVEN tags containing values not present in CARD_TAGS
        WHEN SearchCardsIn.validate_tags is called
        THEN it raises HttpError 400 listing invalid and valid tags
        """
        with self.assertRaises(HttpError) as ctx:
            SearchCardsIn.validate_tags(["Aggro", "NotATag"])

        self.assertEqual(ctx.exception.status_code, 400)
        self.assertIn("Invalid tags", str(ctx.exception))
        self.assertIn("NotATag", str(ctx.exception))

    def test_validate_tags_accepts_valid_tags(self):
        """
        GIVEN tags where all values exist in CARD_TAGS
        WHEN SearchCardsIn.validate_tags is called
        THEN it returns the tags unchanged
        """
        tags = ["Aggro", "Control"]

        result = SearchCardsIn.validate_tags(tags)

        self.assertEqual(result, tags)
