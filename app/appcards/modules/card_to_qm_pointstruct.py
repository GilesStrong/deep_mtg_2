from typing import Any, cast

from appai.tasks.dense_embedding import dense_embed
from beartype import beartype
from celery.result import AsyncResult
from qdrant_client.http import models as qm

from appcards.models import Card
from appcards.modules.card_info import card_to_info


@beartype
def card_to_qm_pointstruct(card: Card) -> qm.PointStruct:
    if card.llm_summary is None:
        raise ValueError("Card must have a summary to be embedded")
    result: AsyncResult = cast(Any, dense_embed.delay)(card.llm_summary)
    dense_vector = cast(list[float], result.get(timeout=60))

    card_info = card_to_info(card)
    payload = {
        "name": card_info.name,
        "text": card_info.text,
        "llm_summary": card_info.llm_summary,
        "subtypes": card_info.subtypes,
        "supertypes": card_info.supertypes,
        "power": card_info.power,
        "toughness": card_info.toughness,
        "mana_cost_red": card_info.mana_cost_red,
        "mana_cost_blue": card_info.mana_cost_blue,
        "mana_cost_green": card_info.mana_cost_green,
        "mana_cost_white": card_info.mana_cost_white,
        "mana_cost_black": card_info.mana_cost_black,
        "mana_cost_colorless": card_info.mana_cost_colorless,
        "converted_mana_cost": card_info.converted_mana_cost,
        "colors": card_info.colors,
        "set_codes": card_info.set_codes,
        "types": card_info.types,
        "rarity": card_info.rarity,
        "keywords": card_info.keywords,
    }
    return qm.PointStruct(
        id=str(card.id),
        vector={"dense": dense_vector},
        payload=payload,
    )
