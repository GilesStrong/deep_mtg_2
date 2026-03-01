from __future__ import annotations

from types import SimpleNamespace

from appauth.models.token import RefreshToken
from appcards.models.card import Card, Rarity
from appcards.models.deck import Deck, DeckCard
from django.test import TestCase
from ninja.errors import HttpError

from appuser.models import User
from appuser.routes.account import delete_account, export_account_data, request_delete_account


class AccountRoutesTests(TestCase):
    """Tests for account data export and deletion routes."""

    def test_export_account_data_returns_profile_decks_and_tokens(self):
        """
        GIVEN an authenticated user with a deck, card, and refresh token
        WHEN export_account_data is called
        THEN the payload includes user profile, deck data, card quantities, and refresh token metadata
        """
        user = User.objects.create(google_id="gid-export", verified=True, warning_count=1)
        deck = Deck.objects.create(name="Export Deck", user=user, short_llm_summary="Short", llm_summary="Long")
        card = Card.objects.create(name="Opt", text="Scry 1.", rarity=Rarity.COMMON)
        DeckCard.objects.create(deck=deck, card=card, quantity=3)
        _token, _raw_token = RefreshToken.mint(user, user_agent="pytest", ip="127.0.0.1")

        result = export_account_data(SimpleNamespace(auth=user))

        self.assertEqual(result.user.id, user.id)
        self.assertEqual(result.user.google_id, "gid-export")
        self.assertEqual(len(result.decks), 1)
        self.assertEqual(result.decks[0].name, "Export Deck")
        self.assertEqual(len(result.decks[0].cards), 1)
        self.assertEqual(result.decks[0].cards[0].card_name, "Opt")
        self.assertEqual(result.decks[0].cards[0].quantity, 3)
        self.assertEqual(len(result.refresh_tokens), 1)
        self.assertEqual(result.refresh_tokens[0].user_agent, "pytest")

    def test_delete_account_removes_user_and_related_records(self):
        """
        GIVEN an authenticated user with decks and refresh tokens
        WHEN delete_account is called with a valid confirmation token
        THEN the user and related records are removed
        """
        user = User.objects.create(google_id="gid-delete", verified=True)
        deck = Deck.objects.create(name="Delete Deck", user=user)
        _token, _raw_token = RefreshToken.mint(user, user_agent="pytest", ip="127.0.0.1")
        confirmation = request_delete_account(SimpleNamespace(auth=user))

        delete_account(SimpleNamespace(auth=user), SimpleNamespace(confirmation_token=confirmation.confirmation_token))

        self.assertFalse(User.objects.filter(id=user.id).exists())
        self.assertFalse(Deck.objects.filter(id=deck.id).exists())
        self.assertFalse(RefreshToken.objects.filter(user_id=user.id).exists())

    def test_delete_account_rejects_invalid_confirmation_token(self):
        """
        GIVEN an authenticated user
        WHEN delete_account is called with an invalid confirmation token
        THEN the route raises HttpError and does not delete the account
        """
        user = User.objects.create(google_id="gid-invalid-token", verified=True)

        with self.assertRaises(HttpError) as context:
            delete_account(SimpleNamespace(auth=user), SimpleNamespace(confirmation_token="invalid-token"))

        self.assertEqual(context.exception.status_code, 400)
        self.assertTrue(User.objects.filter(id=user.id).exists())
