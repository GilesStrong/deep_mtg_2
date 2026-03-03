from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import UUID

from django.test import TestCase

from appai.services.agents.deck_theme import get_daily_deck_theme

_MODULE = "appai.services.agents.deck_theme"


class GetDailyDeckThemeTests(TestCase):
    """Tests for get_daily_deck_theme agent wiring."""

    @patch(f"{_MODULE}.DeckBuildingDeps")
    @patch(f"{_MODULE}.uuid4")
    @patch(f"{_MODULE}.Agent")
    def test_constructs_agent_with_expected_settings_and_returns_output(
        self,
        mock_agent_cls,
        mock_uuid4,
        mock_deps_cls,
    ):
        """
        GIVEN get_daily_deck_theme is called
        WHEN the Agent is constructed and run
        THEN it uses expected model/tools/deps and returns the typed output
        """
        generated_deck_id = UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
        mock_uuid4.return_value = generated_deck_id

        deps_obj = MagicMock()
        mock_deps_cls.return_value = deps_obj

        expected_output = SimpleNamespace(description="A spellslinger deck that recurs instants from graveyard.")
        mock_agent = MagicMock()
        mock_agent.run_sync.return_value = SimpleNamespace(output=expected_output)
        mock_agent_cls.return_value = mock_agent

        result = get_daily_deck_theme()

        self.assertEqual(result, expected_output)
        mock_deps_cls.assert_called_once_with(deck_id=generated_deck_id)
        mock_agent.run_sync.assert_called_once_with(deps=deps_obj)

        agent_kwargs = mock_agent_cls.call_args.kwargs
        self.assertEqual(agent_kwargs["output_type"].__name__, "NewTheme")
        self.assertIs(agent_kwargs["deps_type"], mock_deps_cls)
        self.assertEqual(len(agent_kwargs["tools"]), 2)
        self.assertEqual(agent_kwargs["tools"][0].__name__, "search_for_cards")
        self.assertEqual(agent_kwargs["tools"][1].__name__, "search_for_themes")
