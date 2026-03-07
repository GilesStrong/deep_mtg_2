# Copyright 2026 Giles Strong
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

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
