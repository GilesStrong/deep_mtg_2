from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import TestCase

from appcards.models.card import ManaColorEnum, Rarity, TypeEnum
from appcards.modules.card_info import CardInfo
from appcards.modules.summarise_card import _summarise_card, summarise_card
from appcards.tasks.summarise_card import summarise_card as summarise_card_task

_MODULE = "appcards.modules.summarise_card"
_TASK_MODULE = "appcards.tasks.summarise_card"


def _card_info() -> CardInfo:
    return CardInfo(
        id="12345678-1234-5678-1234-567812345678",
        name="Lightning Bolt",
        text="Deal 3 damage to any target.",
        llm_summary="Classic red burn spell.",
        subtypes=[],
        supertypes=[],
        power=None,
        toughness=None,
        mana_cost_red=1,
        mana_cost_blue=0,
        mana_cost_green=0,
        mana_cost_white=0,
        mana_cost_black=0,
        mana_cost_colorless=0,
        converted_mana_cost=1,
        colors=[ManaColorEnum.RED],
        set_codes=["FDN"],
        types=[TypeEnum.INSTANT],
        rarity=Rarity.COMMON,
        keywords=[],
    )


class SummariseCardModuleTests(TestCase):
    """Tests for appcards.modules.summarise_card."""

    @patch(f"{_MODULE}.Agent")
    def test_private_summarise_uses_agent_output(self, mock_agent_cls):
        """
        GIVEN card details and a mocked LLM agent response
        WHEN _summarise_card is called
        THEN it returns the agent output text
        """
        mock_agent = MagicMock()
        mock_agent.run_sync.return_value = SimpleNamespace(output="A strong cheap burn spell.")
        mock_agent_cls.return_value = mock_agent

        result = _summarise_card(_card_info())

        self.assertEqual(result, "A strong cheap burn spell.")
        mock_agent.run_sync.assert_called_once()

    @patch(f"{_MODULE}.in_celery_task", return_value=False)
    @patch(f"{_MODULE}._summarise_card")
    def test_summarise_card_direct_path_outside_celery(self, mock_private, _mock_in_celery):
        """
        GIVEN execution outside a Celery worker
        WHEN summarise_card is called
        THEN it calls the private local summariser directly
        """
        mock_private.return_value = "direct summary"

        result = summarise_card(_card_info())

        self.assertEqual(result, "direct summary")
        mock_private.assert_called_once()

    @patch(f"{_MODULE}.in_celery_task", return_value=True)
    def test_summarise_card_celery_path_uses_task_delay(self, _mock_in_celery):
        """
        GIVEN execution inside a Celery worker context
        WHEN summarise_card is called
        THEN it delegates through the task delay/get flow and returns that result
        """
        details = _card_info()
        with patch("appcards.tasks.summarise_card.summarise_card") as mock_task:
            mock_async_result = MagicMock()
            mock_async_result.get.return_value = "queued summary"
            mock_task.delay.return_value = mock_async_result

            result = summarise_card(details)

        self.assertEqual(result, "queued summary")
        mock_task.delay.assert_called_once()


class SummariseCardTaskTests(TestCase):
    """Tests for appcards.tasks.summarise_card."""

    @patch(f"{_TASK_MODULE}._summarise_card")
    def test_task_validates_payload_and_delegates(self, mock_private):
        """
        GIVEN a dict payload accepted by CardInfo validation
        WHEN summarise_card task is called
        THEN it validates payload into CardInfo and delegates to _summarise_card
        """
        mock_private.return_value = "task summary"

        result = summarise_card_task.run(card_details=_card_info().model_dump(mode="python"))

        self.assertEqual(result, "task summary")
        mock_private.assert_called_once()
