from __future__ import annotations

from unittest.mock import patch

from django.test import TestCase

from appauth.modules.google_auth import verify_google_token

_MODULE = "appauth.modules.google_auth"


class VerifyGoogleTokenTests(TestCase):
    """Tests for verify_google_token."""

    @patch(f"{_MODULE}.APP_SETTINGS")
    @patch(f"{_MODULE}.requests.Request")
    @patch(f"{_MODULE}.id_token.verify_oauth2_token")
    def test_returns_verified_result_for_valid_issuer(self, mock_verify, mock_request, mock_settings):
        """
        GIVEN a Google ID token with a valid issuer and verified email
        WHEN verify_google_token is called
        THEN it returns a verified result with the Google user ID
        """
        mock_settings.GOOGLE_CLIENT_ID = "google-client-id"
        mock_verify.return_value = {
            "iss": "accounts.google.com",
            "email_verified": True,
            "sub": "google-user-123",
        }

        result = verify_google_token("id-token")

        mock_verify.assert_called_once_with("id-token", mock_request.return_value, "google-client-id")
        self.assertTrue(result.verified)
        self.assertEqual(result.google_id, "google-user-123")

    @patch(f"{_MODULE}.APP_SETTINGS")
    @patch(f"{_MODULE}.requests.Request")
    @patch(f"{_MODULE}.id_token.verify_oauth2_token")
    def test_raises_for_wrong_issuer(self, mock_verify, _mock_request, mock_settings):
        """
        GIVEN a Google ID token whose issuer is not accepted
        WHEN verify_google_token is called
        THEN it raises ValueError
        """
        mock_settings.GOOGLE_CLIENT_ID = "google-client-id"
        mock_verify.return_value = {
            "iss": "https://malicious.example.com",
            "email_verified": True,
            "sub": "google-user-123",
        }

        with self.assertRaises(ValueError):
            verify_google_token("id-token")
