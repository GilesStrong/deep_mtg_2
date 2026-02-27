from __future__ import annotations

from django.test import TestCase

from appai.api import router


class ApiRouterTests(TestCase):
    """Tests for appai API router composition."""

    def test_registers_deck_prefix_routes(self):
        """
        GIVEN the app-level AI router configuration
        WHEN inspecting mounted sub-routers
        THEN one sub-router is mounted at the '/deck' prefix
        """
        prefixes = [prefix for prefix, _sub_router in router._routers]
        self.assertIn("/deck", prefixes)
