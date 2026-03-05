from __future__ import annotations

from appuser.models import User
from django.test import TestCase

from appcards.models.card import Card, Rarity
from appcards.models.deck import Deck, DeckCard
from appcards.modules.deck_info import get_colors_from_deck


class GetColorsFromDeckTests(TestCase):
    """Tests for get_colors_from_deck."""

    def test_returns_union_of_colors_from_color_identity_tags(self):
        """
        GIVEN a deck tagged with multiple color identity labels
        WHEN get_colors_from_deck is called
        THEN it returns the union of mapped mana colors from those identities
        """
        user = User.objects.create(google_id="colors-gid-1", verified=True)
        deck = Deck.objects.create(name="Tagged Colors", user=user, tags=["Azorius", "Rakdos", "Aggro"])

        result = get_colors_from_deck(deck)

        self.assertEqual(result, {"W", "U", "B", "R"})

    def test_falls_back_to_card_colors_when_no_color_identity_tag_present(self):
        """
        GIVEN a deck whose tags do not include any color identity labels
        WHEN get_colors_from_deck is called
        THEN it falls back to collecting colors from related cards
        """
        user = User.objects.create(google_id="colors-gid-2", verified=True)
        deck = Deck.objects.create(name="Fallback From Cards", user=user, tags=["Aggro", "GoWide"])
        card_one = Card.objects.create(name="Card Green", text="", rarity=Rarity.COMMON, colors=["G"])
        card_two = Card.objects.create(name="Card BlueWhite", text="", rarity=Rarity.COMMON, colors=["U", "W"])
        DeckCard.objects.create(deck=deck, card=card_one, quantity=1)
        DeckCard.objects.create(deck=deck, card=card_two, quantity=1)

        result = get_colors_from_deck(deck)

        self.assertEqual(result, {"G", "U", "W"})

    def test_falls_back_to_card_colors_when_tags_is_none(self):
        """
        GIVEN a deck object with tags set to None in-memory
        WHEN get_colors_from_deck is called
        THEN it bypasses tag parsing and uses related card colors
        """
        user = User.objects.create(google_id="colors-gid-3", verified=True)
        deck = Deck.objects.create(name="None Tags", user=user, tags=["MonoRed"])
        card = Card.objects.create(name="Card Black", text="", rarity=Rarity.COMMON, colors=["B"])
        DeckCard.objects.create(deck=deck, card=card, quantity=1)

        deck.tags = None

        result = get_colors_from_deck(deck)

        self.assertEqual(result, {"B"})

    def test_returns_empty_set_for_colorless_identity(self):
        """
        GIVEN a deck tagged as Colorless
        WHEN get_colors_from_deck is called
        THEN it returns an empty set from color identity mapping
        """
        user = User.objects.create(google_id="colors-gid-4", verified=True)
        deck = Deck.objects.create(name="Colorless Tagged", user=user, tags=["Colorless"])
        colored_card = Card.objects.create(name="Card Red", text="", rarity=Rarity.COMMON, colors=["R"])
        DeckCard.objects.create(deck=deck, card=colored_card, quantity=1)

        result = get_colors_from_deck(deck)

        self.assertEqual(result, set())
