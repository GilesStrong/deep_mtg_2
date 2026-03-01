from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

from appuser.models import User
from django.test import TestCase
from ninja.errors import HttpError

from appcards.constants.cards import HIERACHICAL_TAGS
from appcards.models.card import Card, Rarity
from appcards.models.deck import Deck
from appcards.models.printing import Printing
from appcards.routes.card import get_card, list_set_codes, list_tags
from appcards.routes.deck import delete_deck, get_summary_deck

_CARD_MODULE = "appcards.routes.card"


class CardRoutesTests(TestCase):
    """Tests for appcards card routes."""

    def test_list_tags_returns_hierarchical_mapping_with_used_subtags_only(self):
        """
        GIVEN cards with overlapping tag lists
        WHEN list_tags is called
        THEN it returns all primary tags with only used subtags populated
        """
        Card.objects.create(name="Opt", text="Scry 1.", rarity=Rarity.COMMON, tags=["Control", "Cantrip"])
        Card.objects.create(name="Shock", text="Deal 2 damage.", rarity=Rarity.COMMON, tags=["Aggro", "Control"])
        Card.objects.create(name="Llanowar Elves", text="Add G.", rarity=Rarity.COMMON, tags=["Ramp"])

        result = list_tags(SimpleNamespace())

        self.assertEqual(result.tags["CardAdvantage"], {"Cantrip": HIERACHICAL_TAGS["CardAdvantage"]["Cantrip"]})
        self.assertEqual(
            result.tags,
            {
                primary_tag: {subtag: description for subtag, description in subtags.items() if subtag == "Cantrip"}
                for primary_tag, subtags in HIERACHICAL_TAGS.items()
            },
        )

    def test_list_set_codes_returns_distinct_sorted_values(self):
        """
        GIVEN multiple printings including duplicate set codes
        WHEN list_set_codes is called
        THEN it returns distinct set codes in ascending order
        """
        card = Card.objects.create(name="Opt", text="Scry 1.", rarity=Rarity.COMMON)
        Printing.objects.create(card=card, set_code="M20")
        Printing.objects.create(card=card, set_code="FDN")

        card2 = Card.objects.create(name="Shock", text="Deal 2 damage.", rarity=Rarity.COMMON)
        Printing.objects.create(card=card2, set_code="FDN")

        result = list_set_codes(SimpleNamespace())

        self.assertEqual(result.set_codes, ["FDN", "M20"])

    @patch(f"{_CARD_MODULE}.card_to_info")
    def test_get_card_returns_card_info_for_path_param_card(self, mock_card_to_info):
        """
        GIVEN path params that already resolve to a card instance
        WHEN get_card is called
        THEN it delegates to card_to_info and returns that value
        """
        card = Card.objects.create(name="Consider", text="Draw then mill.", rarity=Rarity.COMMON)
        expected = SimpleNamespace(name="Consider")
        mock_card_to_info.return_value = expected

        result = get_card(SimpleNamespace(), SimpleNamespace(card=card))

        self.assertEqual(result, expected)


class DeckRoutesTests(TestCase):
    """Tests for appcards deck routes."""

    def test_get_summary_deck_blocks_non_owner(self):
        """
        GIVEN a deck owned by another user
        WHEN get_summary_deck is called by the current user
        THEN it raises HttpError 403
        """
        owner = User.objects.create(google_id="owner-gid", verified=True)
        other = User.objects.create(google_id="other-gid", verified=True)
        deck = Deck.objects.create(name="Owner Deck", user=owner)

        request = SimpleNamespace(auth=other)
        with self.assertRaises(HttpError) as ctx:
            get_summary_deck(request, SimpleNamespace(deck=deck))

        self.assertEqual(ctx.exception.status_code, 403)

    def test_delete_deck_allows_owner(self):
        """
        GIVEN a deck owned by the authenticated user
        WHEN delete_deck is called
        THEN the deck is deleted and None is returned
        """
        user = User.objects.create(google_id="delete-gid", verified=True)
        deck = Deck.objects.create(name="Delete Me", user=user)

        result = delete_deck(SimpleNamespace(auth=user), SimpleNamespace(deck=deck))

        self.assertIsNone(result)
        self.assertFalse(Deck.objects.filter(id=deck.id).exists())
