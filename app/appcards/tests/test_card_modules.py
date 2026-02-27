from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

from django.test import TestCase

from appcards.models.card import Card, Rarity
from appcards.models.printing import Printing
from appcards.modules.card_info import card_to_info
from appcards.modules.card_to_qm_pointstruct import card_to_qm_pointstruct

_MODULE_QM = "appcards.modules.card_to_qm_pointstruct"


class CardToInfoTests(TestCase):
    """Tests for card_to_info."""

    def test_includes_printing_set_codes(self):
        """
        GIVEN a card with multiple printings
        WHEN card_to_info is called
        THEN the returned CardInfo includes all related set codes
        """
        card = Card.objects.create(name="Lightning Bolt", text="Deal 3 damage.", rarity=Rarity.COMMON)
        Printing.objects.create(card=card, set_code="M10")
        Printing.objects.create(card=card, set_code="FDN")

        result = card_to_info(card)

        self.assertEqual(result.name, "Lightning Bolt")
        self.assertCountEqual(result.set_codes, ["M10", "FDN"])


class CardToQmPointStructTests(TestCase):
    """Tests for card_to_qm_pointstruct."""

    def test_raises_when_llm_summary_missing(self):
        """
        GIVEN a card without an llm_summary
        WHEN card_to_qm_pointstruct is called
        THEN it raises ValueError because embedding input is missing
        """
        card = Card.objects.create(name="Opt", text="Scry 1, draw a card.", rarity=Rarity.COMMON, llm_summary=None)

        with self.assertRaises(ValueError):
            card_to_qm_pointstruct(card)

    @patch(f"{_MODULE_QM}.qm.PointStruct")
    @patch(f"{_MODULE_QM}.card_to_info")
    @patch(f"{_MODULE_QM}.dense_embed")
    def test_builds_point_struct_with_dense_vector_and_payload(self, mock_dense_embed, mock_card_to_info, mock_point):
        """
        GIVEN a card with summary and successful embedding/payload conversion
        WHEN card_to_qm_pointstruct is called
        THEN it builds a PointStruct using dense vector and JSON payload
        """
        card = Card.objects.create(
            name="Counterspell",
            text="Counter target spell.",
            rarity=Rarity.UNCOMMON,
            llm_summary="A cheap blue interaction card.",
        )
        mock_dense_embed.return_value = [0.1, 0.2, 0.3]
        mock_card_to_info.return_value = SimpleNamespace(model_dump=lambda mode="json": {"name": "Counterspell"})

        result = card_to_qm_pointstruct(card)

        mock_point.assert_called_once_with(
            id=str(card.id),
            vector={"dense": [0.1, 0.2, 0.3]},
            payload={"name": "Counterspell"},
        )
        self.assertEqual(result, mock_point.return_value)
