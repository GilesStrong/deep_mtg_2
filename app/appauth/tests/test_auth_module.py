from __future__ import annotations

from types import SimpleNamespace

from django.test import TestCase

from appauth.modules.auth import get_user_from_request


class GetUserFromRequestTests(TestCase):
    """Tests for get_user_from_request."""

    def test_returns_auth_when_present(self):
        """
        GIVEN a request-like object with an auth attribute
        WHEN get_user_from_request is called
        THEN it returns the auth object
        """
        user = SimpleNamespace(id="u1")
        request = SimpleNamespace(auth=user)

        result = get_user_from_request(request)

        self.assertEqual(result, user)

    def test_raises_value_error_when_auth_missing(self):
        """
        GIVEN a request-like object without an auth attribute
        WHEN get_user_from_request is called
        THEN it raises ValueError with a helpful message
        """
        with self.assertRaises(ValueError) as ctx:
            get_user_from_request(SimpleNamespace())

        self.assertIn("auth", str(ctx.exception))
