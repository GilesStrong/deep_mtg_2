from __future__ import annotations

from django.test import TestCase

from appauth.api import router


class ApiRouterTests(TestCase):
    """Tests for appauth API router composition."""

    def test_registers_token_router_at_root_prefix(self):
        """
        GIVEN the appauth top-level router configuration
        WHEN inspecting mounted sub-routers
        THEN the token router is mounted at the empty prefix
        """
        prefixes = [prefix for prefix, _sub_router in router._routers]
        self.assertIn("", prefixes)
