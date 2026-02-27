from __future__ import annotations

from django.test import TestCase

from appcards.api import router


class ApiRouterTests(TestCase):
    """Tests for appcards API router composition."""

    def test_registers_card_and_deck_prefixes(self):
        """
        GIVEN the appcards top-level router
        WHEN inspecting mounted sub-routers
        THEN both '/card' and '/deck' prefixes are registered
        """
        prefixes = [prefix for prefix, _sub_router in router._routers]
        self.assertIn('/card', prefixes)
        self.assertIn('/deck', prefixes)
