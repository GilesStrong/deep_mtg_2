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

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import TestCase

from appai.services.agents.deck_theme import get_daily_deck_theme

_MODULE = "appai.services.agents.deck_theme"


class GetDailyDeckThemeTests(TestCase):
    """Tests for get_daily_deck_theme agent wiring."""

    @patch(f"{_MODULE}.Agent")
    def test_constructs_agent_with_expected_settings_and_returns_output(
        self,
        mock_agent_cls,
    ):
        """
        GIVEN get_daily_deck_theme is called
        WHEN the Agent is constructed and run
        THEN it uses expected model/tools and returns the typed output
        """
        expected_output = SimpleNamespace(description="A spellslinger deck that recurs instants from graveyard.")
        mock_agent = MagicMock()
        mock_agent.run_sync.return_value = SimpleNamespace(output=expected_output)
        mock_agent_cls.return_value = mock_agent

        result = get_daily_deck_theme()

        self.assertEqual(result, expected_output)
        mock_agent.run_sync.assert_called_once_with()

        agent_kwargs = mock_agent_cls.call_args.kwargs
        self.assertEqual(agent_kwargs["output_type"].__name__, "NewTheme")
        self.assertIn("tools", agent_kwargs)
        self.assertEqual(len(agent_kwargs["tools"]), 1)
