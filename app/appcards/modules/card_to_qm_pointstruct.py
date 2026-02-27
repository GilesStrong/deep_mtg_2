from appai.modules.dense_embedding import dense_embed
from appcore.modules.beartype import beartype
from qdrant_client.http import models as qm

from appcards.models import Card
from appcards.modules.card_info import card_to_info


@beartype
def card_to_qm_pointstruct(card: Card) -> qm.PointStruct:
    if card.llm_summary is None:
        raise ValueError("Card must have a summary to be embedded")
    dense_vector = dense_embed(card.llm_summary)

    card_info = card_to_info(card)
    return qm.PointStruct(
        id=str(card.id),
        vector={"dense": dense_vector},
        payload=card_info.model_dump(mode="json"),
    )
