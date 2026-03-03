from __future__ import annotations

from uuid import UUID

from appuser.models import User
from django.test import TestCase

from appcards.models.card import Card, Rarity
from appcards.models.deck import Deck, DeckCard, validate_deck_basic
from appcards.models.printing import Printing


class ValidateDeckBasicTests(TestCase):
    """Tests for validate_deck_basic."""

    def test_returns_not_found_for_missing_uuid(self):
        """
        GIVEN a deck UUID that does not exist
        WHEN validate_deck_basic is called
        THEN it returns an invalid result with a does-not-exist issue
        """
        result = validate_deck_basic(UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"))

        self.assertFalse(result.valid)
        self.assertIn("Deck does not exist", result.issues)
        self.assertEqual(result.total_cards, 0)

    def test_invalid_when_less_than_sixty_cards(self):
        """
        GIVEN a deck with fewer than 60 total cards
        WHEN validate_deck_basic is called
        THEN it returns invalid with a minimum-cards issue
        """
        user = User.objects.create(google_id="deck-gid-1", verified=True)
        deck = Deck.objects.create(name="Small Deck", user=user)
        card = Card.objects.create(name="Island", text="Basic land", rarity=Rarity.COMMON, supertypes=["Basic"])
        DeckCard.objects.create(deck=deck, card=card, quantity=20)

        result = validate_deck_basic(deck)

        self.assertFalse(result.valid)
        self.assertEqual(result.total_cards, 20)
        self.assertTrue(any("minimum is 60" in issue for issue in result.issues))

    def test_invalid_when_non_basic_has_more_than_four_copies(self):
        """
        GIVEN a deck containing over 4 copies of a non-basic card
        WHEN validate_deck_basic is called
        THEN it returns invalid with an over-copy issue
        """
        user = User.objects.create(google_id="deck-gid-2", verified=True)
        deck = Deck.objects.create(name="Too Many Copies", user=user)
        filler = Card.objects.create(name="Forest", text="Basic land", rarity=Rarity.COMMON, supertypes=["Basic"])
        non_basic = Card.objects.create(name="Shock", text="Deal 2 damage", rarity=Rarity.COMMON, supertypes=[])
        DeckCard.objects.create(deck=deck, card=filler, quantity=56)
        DeckCard.objects.create(deck=deck, card=non_basic, quantity=5)

        result = validate_deck_basic(deck)

        self.assertFalse(result.valid)
        self.assertTrue(any("copies of 'Shock'" in issue for issue in result.issues))

    def test_valid_at_sixty_cards_with_legal_copy_counts(self):
        """
        GIVEN a deck with 60 cards and legal copy counts
        WHEN validate_deck_basic is called
        THEN it returns a valid result
        """
        user = User.objects.create(google_id="deck-gid-3", verified=True)
        deck = Deck.objects.create(name="Valid Deck", user=user)
        basic = Card.objects.create(name="Mountain", text="Basic land", rarity=Rarity.COMMON, supertypes=["Basic"])
        spell = Card.objects.create(name="Lightning Strike", text="Deal 3 damage", rarity=Rarity.UNCOMMON)
        DeckCard.objects.create(deck=deck, card=basic, quantity=56)
        DeckCard.objects.create(deck=deck, card=spell, quantity=4)

        result = validate_deck_basic(deck)

        self.assertTrue(result.valid)
        self.assertEqual(result.total_cards, 60)


class DeckSaveBehaviorTests(TestCase):
    """Tests for Deck.save behavior updating set codes and validity."""

    def test_tags_default_to_empty_list(self):
        """
        GIVEN a newly created deck without explicit tags
        WHEN it is read back from the database
        THEN tags defaults to an empty list
        """
        user = User.objects.create(google_id="deck-gid-tags-1", verified=True)
        deck = Deck.objects.create(name="Untagged Deck", user=user)

        deck.refresh_from_db()

        self.assertEqual(deck.tags, [])

    def test_tags_are_persisted(self):
        """
        GIVEN a deck created with tags
        WHEN it is saved and refreshed
        THEN the same tags are persisted on the deck
        """
        user = User.objects.create(google_id="deck-gid-tags-2", verified=True)
        deck = Deck.objects.create(name="Tagged Deck", user=user, tags=["Aggro", "Midrange"])

        deck.refresh_from_db()

        self.assertCountEqual(deck.tags, ["Aggro", "Midrange"])

    def test_save_updates_set_codes_from_printings(self):
        """
        GIVEN an existing deck with cards that have printings
        WHEN deck.save is called
        THEN set_codes is recalculated from related card printings
        """
        user = User.objects.create(google_id="deck-gid-4", verified=True)
        deck = Deck.objects.create(name="SetCode Deck", user=user)
        card = Card.objects.create(name="Opt", text="Scry 1", rarity=Rarity.COMMON)
        Printing.objects.create(card=card, set_code="FDN")
        Printing.objects.create(card=card, set_code="M20")
        DeckCard.objects.create(deck=deck, card=card, quantity=60)

        deck.save()
        deck.refresh_from_db()

        self.assertCountEqual(deck.set_codes, ["FDN", "M20"])
