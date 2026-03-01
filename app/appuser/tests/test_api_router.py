from __future__ import annotations

from django.test import TestCase

from appuser.api import router


class ApiRouterTests(TestCase):
    """Tests for appuser API router composition."""

    def test_registers_account_router_at_root_prefix(self):
        """
        GIVEN the appuser top-level router configuration
        WHEN inspecting mounted sub-routers
        THEN the account router is mounted at the empty prefix
        """
        prefixes = [prefix for prefix, _sub_router in router._routers]
        self.assertIn('', prefixes)
