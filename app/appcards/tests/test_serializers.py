from __future__ import annotations

from types import SimpleNamespace
from uuid import UUID

from appuser.models import User
from django.test import TestCase
from ninja.errors import HttpError

from appcards.models.card import Card, Rarity
from appcards.models.deck import Deck
from appcards.serializers.card import GetCardIn
from appcards.serializers.deck import GetDeckIn, GetFullDeckOut, GetSummaryDeckOut


class GetCardInTests(TestCase):
    """Tests for GetCardIn.card property behavior."""

    def test_resolves_card_from_card_id(self):
        """
        GIVEN a valid card_id in GetCardIn
        WHEN .card is accessed
        THEN it returns the matching Card instance
        """
        card = Card.objects.create(name="Opt", text="Scry 1", rarity=Rarity.COMMON)
        payload = GetCardIn(card_id=card.id)

        result = payload.card

        self.assertEqual(result.id, card.id)

    def test_raises_404_for_missing_card(self):
        """
        GIVEN a card_id that does not exist
        WHEN .card is accessed
        THEN it raises HttpError 404
        """
        payload = GetCardIn(card_id=UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"))

        with self.assertRaises(HttpError) as ctx:
            _ = payload.card

        self.assertEqual(ctx.exception.status_code, 404)

    def test_card_property_is_cached(self):
        """
        GIVEN a valid GetCardIn instance
        WHEN .card is accessed multiple times
        THEN it returns the same cached object instance
        """
        card = Card.objects.create(name="Shock", text="Deal 2 damage", rarity=Rarity.COMMON)
        payload = GetCardIn(card_id=card.id)

        first = payload.card
        second = payload.card

        self.assertIs(first, second)


class GetDeckInTests(TestCase):
    """Tests for GetDeckIn.deck property behavior."""

    def test_resolves_deck_from_deck_id(self):
        """
        GIVEN a valid deck_id in GetDeckIn
        WHEN .deck is accessed
        THEN it returns the matching Deck instance
        """
        user = User.objects.create(google_id="gid-deck-in-1", verified=True)
        deck = Deck.objects.create(name="Control", user=user)
        payload = GetDeckIn(deck_id=deck.id)

        result = payload.deck

        self.assertEqual(result.id, deck.id)

    def test_raises_404_for_missing_deck(self):
        """
        GIVEN a deck_id that does not exist
        WHEN .deck is accessed
        THEN it raises HttpError 404
        """
        payload = GetDeckIn(deck_id=UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"))

        with self.assertRaises(HttpError) as ctx:
            _ = payload.deck

        self.assertEqual(ctx.exception.status_code, 404)


class DeckOutputValidatorTests(TestCase):
    """Tests for appcards deck serializer output validators."""

    def test_summary_out_validate_id_raises_for_missing_deck(self):
        """
        GIVEN a deck ID that does not exist
        WHEN GetSummaryDeckOut.validate_id is called
        THEN it raises RuntimeError
        """
        with self.assertRaises(RuntimeError):
            GetSummaryDeckOut.validate_id(UUID("cccccccc-cccc-cccc-cccc-cccccccccccc"))

    def test_full_out_validate_cards_rejects_invalid_quantity(self):
        """
        GIVEN a cards payload containing a quantity less than 1
        WHEN GetFullDeckOut.validate_cards is called
        THEN it raises RuntimeError for invalid quantity
        """
        card = SimpleNamespace(id=UUID("dddddddd-dddd-dddd-dddd-dddddddddddd"))

        with self.assertRaises(RuntimeError):
            GetFullDeckOut.validate_cards([(0, card)])

    def test_summary_out_includes_tags(self):
        """
        GIVEN a valid deck and summary payload with tags
        WHEN GetSummaryDeckOut is constructed
        THEN tags are preserved on the output object
        """
        user = User.objects.create(google_id="gid-summary-tags", verified=True)
        deck = Deck.objects.create(name="Tagged Summary Deck", user=user, tags=["Aggro", "Burn"])

        output = GetSummaryDeckOut(
            id=deck.id,
            name=deck.name,
            short_summary="Fast red pressure",
            set_codes=[],
            tags=["Aggro", "Burn"],
            date_updated="2026-03-03T00:00:00+00:00",
            generation_status=None,
            generation_task_id=None,
        )

        self.assertCountEqual(output.tags, ["Aggro", "Burn"])

    def test_full_out_includes_tags(self):
        """
        GIVEN a valid deck and full payload with tags
        WHEN GetFullDeckOut is constructed
        THEN tags are preserved on the output object
        """
        user = User.objects.create(google_id="gid-full-tags", verified=True)
        deck = Deck.objects.create(name="Tagged Full Deck", user=user, tags=["Control", "Midrange"])

        output = GetFullDeckOut(
            id=deck.id,
            name=deck.name,
            short_summary="Flexible plan",
            full_summary="Longer explanation of the strategy and card roles.",
            set_codes=[],
            tags=["Control", "Midrange"],
            date_updated="2026-03-03T00:00:00+00:00",
            cards=[],
            creation_status=None,
        )

        self.assertCountEqual(output.tags, ["Control", "Midrange"])
