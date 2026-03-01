from __future__ import annotations

from datetime import timedelta
from unittest.mock import patch

from appuser.models import User
from django.test import TestCase
from django.utils import timezone

from appauth.models.token import RefreshToken

_MODULE = "appauth.models.token"


class RefreshTokenModelTests(TestCase):
    """Tests for RefreshToken model behavior."""

    @patch(f"{_MODULE}.APP_SETTINGS")
    @patch(f"{_MODULE}.secrets.token_urlsafe")
    def test_mint_persists_token_with_expected_fields(self, mock_token_urlsafe, mock_settings):
        """
        GIVEN a user and refresh token settings
        WHEN RefreshToken.mint is called
        THEN it creates a refresh token record with bounded user_agent and expected token value
        """
        mock_settings.REFRESH_TOKEN_TTL_SECONDS = 3600
        mock_token_urlsafe.return_value = "refresh-token-value"
        user = User.objects.create(google_id="gid-model-1", verified=True, warning_count=0)

        token, raw_token = RefreshToken.mint(user, user_agent="x" * 1200, ip="127.0.0.1")

        self.assertEqual(raw_token, "refresh-token-value")
        self.assertEqual(token.token, RefreshToken.hash_token("refresh-token-value"))
        self.assertEqual(token.user_id, user.id)
        self.assertEqual(token.user_agent, "x" * 1000)
        self.assertEqual(token.ip, "127.0.0.1")
        self.assertGreater(token.expires_at, timezone.now())

    def test_is_valid_false_when_revoked(self):
        """
        GIVEN a refresh token with revoked_at set
        WHEN is_valid is called
        THEN it returns False
        """
        user = User.objects.create(google_id="gid-model-2", verified=True, warning_count=0)
        token, _raw_token = RefreshToken.mint(user)
        token.revoked_at = timezone.now()
        token.save(update_fields=["revoked_at"])

        self.assertFalse(token.is_valid())

    def test_is_valid_false_when_expired(self):
        """
        GIVEN a refresh token with expires_at in the past
        WHEN is_valid is called
        THEN it returns False
        """
        user = User.objects.create(google_id="gid-model-3", verified=True, warning_count=0)
        token, _raw_token = RefreshToken.mint(user)
        token.expires_at = timezone.now() - timedelta(seconds=1)
        token.save(update_fields=["expires_at"])

        self.assertFalse(token.is_valid())

    def test_is_valid_true_when_not_revoked_and_not_expired(self):
        """
        GIVEN a refresh token that is not revoked and not expired
        WHEN is_valid is called
        THEN it returns True
        """
        user = User.objects.create(google_id="gid-model-4", verified=True, warning_count=0)
        token, _raw_token = RefreshToken.mint(user)

        self.assertTrue(token.is_valid())
