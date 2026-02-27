from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

from appuser.models import User
from django.test import TestCase
from ninja.errors import HttpError

from appauth.models.token import RefreshToken
from appauth.routes.token import exchange, refresh

_MODULE = "appauth.routes.token"


class ExchangeRouteTests(TestCase):
    """Tests for exchange route."""

    @patch(f"{_MODULE}.verify_google_token")
    def test_rejects_unverified_email(self, mock_verify):
        """
        GIVEN a Google token verification result with verified=False
        WHEN exchange is called
        THEN it raises HttpError 401
        """
        mock_verify.return_value = SimpleNamespace(verified=False, google_id="gid-1")

        request = SimpleNamespace(headers={}, META={})
        payload = SimpleNamespace(google_id_token="google-token")

        with self.assertRaises(HttpError) as ctx:
            exchange(request, payload)

        self.assertEqual(ctx.exception.status_code, 401)

    @patch(f"{_MODULE}.verify_google_token")
    @patch(f"{_MODULE}.APP_SETTINGS")
    def test_rejects_blocked_user(self, mock_settings, mock_verify):
        """
        GIVEN a verified Google identity and a user at or above warning threshold
        WHEN exchange is called
        THEN it raises HttpError 403
        """
        mock_settings.N_WARNINGS_BEFORE_BLOCK = 3
        mock_verify.return_value = SimpleNamespace(verified=True, google_id="gid-blocked")
        User.objects.create(google_id="gid-blocked", verified=True, warning_count=3)

        request = SimpleNamespace(headers={}, META={})
        payload = SimpleNamespace(google_id_token="google-token")

        with self.assertRaises(HttpError) as ctx:
            exchange(request, payload)

        self.assertEqual(ctx.exception.status_code, 403)

    @patch(f"{_MODULE}.mint_access_token")
    @patch(f"{_MODULE}.RefreshToken")
    @patch(f"{_MODULE}.verify_google_token")
    @patch(f"{_MODULE}.APP_SETTINGS")
    def test_returns_tokens_for_verified_user(self, mock_settings, mock_verify, mock_refresh_token, mock_mint):
        """
        GIVEN a verified Google identity and allowed user
        WHEN exchange is called
        THEN it returns an access token and a newly minted refresh token
        """
        mock_settings.N_WARNINGS_BEFORE_BLOCK = 3
        mock_verify.return_value = SimpleNamespace(verified=True, google_id="gid-ok")
        mock_mint.return_value = "access-token"
        mock_refresh_token.mint.return_value = SimpleNamespace(token="refresh-token")

        request = SimpleNamespace(headers={"User-Agent": "pytest"}, META={"REMOTE_ADDR": "127.0.0.1"})
        payload = SimpleNamespace(google_id_token="google-token")

        result = exchange(request, payload)

        self.assertEqual(result.access_token, "access-token")
        self.assertEqual(result.refresh_token, "refresh-token")


class RefreshRouteTests(TestCase):
    """Tests for refresh route."""

    def test_rejects_missing_refresh_token(self):
        """
        GIVEN a refresh token value not present in storage
        WHEN refresh is called
        THEN it raises HttpError 401
        """
        request = SimpleNamespace(headers={}, META={})
        payload = SimpleNamespace(refresh_token="missing-token")

        with self.assertRaises(HttpError) as ctx:
            refresh(request, payload)

        self.assertEqual(ctx.exception.status_code, 401)

    def test_rejects_invalid_refresh_token(self):
        """
        GIVEN an existing refresh token that is expired or revoked
        WHEN refresh is called
        THEN it raises HttpError 401 and does not mint new tokens
        """
        user = User.objects.create(google_id="gid-refresh-invalid", verified=True, warning_count=0)
        rt = RefreshToken.mint(user, user_agent="ua", ip="127.0.0.1")
        rt.revoked_at = __import__("django.utils.timezone").utils.timezone.now()
        rt.save(update_fields=["revoked_at"])

        request = SimpleNamespace(headers={}, META={})
        payload = SimpleNamespace(refresh_token=rt.token)

        with (
            patch(f"{_MODULE}.mint_access_token") as mock_mint_access,
            patch(f"{_MODULE}.RefreshToken.mint") as mock_mint_refresh,
        ):
            with self.assertRaises(HttpError) as ctx:
                refresh(request, payload)

        self.assertEqual(ctx.exception.status_code, 401)
        mock_mint_access.assert_not_called()
        mock_mint_refresh.assert_not_called()

    def test_rotates_refresh_and_returns_new_tokens(self):
        """
        GIVEN a valid refresh token
        WHEN refresh is called
        THEN it revokes the old token, mints a new refresh token, and returns new access and refresh tokens
        """
        user = User.objects.create(google_id="gid-refresh-ok", verified=True, warning_count=0)
        old_rt = RefreshToken.mint(user, user_agent="ua", ip="127.0.0.1")

        request = SimpleNamespace(headers={"User-Agent": "pytest"}, META={"REMOTE_ADDR": "127.0.0.1"})
        payload = SimpleNamespace(refresh_token=old_rt.token)

        with (
            patch(f"{_MODULE}.mint_access_token") as mock_mint_access,
            patch(f"{_MODULE}.RefreshToken.mint") as mock_mint_refresh,
        ):
            mock_mint_access.return_value = "new-access-token"
            mock_mint_refresh.return_value = SimpleNamespace(token="new-refresh-token")

            result = refresh(request, payload)

        old_rt.refresh_from_db()
        self.assertIsNotNone(old_rt.revoked_at)
        self.assertEqual(result.access_token, "new-access-token")
        self.assertEqual(result.refresh_token, "new-refresh-token")
