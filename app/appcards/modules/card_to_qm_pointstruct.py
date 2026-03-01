from appai.modules.dense_embedding import dense_embed
from appcore.modules.beartype import beartype
from qdrant_client.http import models as qm

from appcards.models import Card
from appcards.modules.card_info import card_to_info


@beartype
def card_to_qm_pointstruct(card: Card) -> qm.PointStruct:
    """
    Convert a Card object to a Qdrant PointStruct for vector storage.

    This function takes a Card object, generates a dense vector embedding from
    the card's LLM summary, and packages it along with the card's information
    into a Qdrant PointStruct suitable for upserting into a Qdrant collection.

    Args:
        card (Card): The card object to convert. Must have a non-None `llm_summary`
                     attribute to generate the dense vector embedding.

    Returns:
        qm.PointStruct: A Qdrant PointStruct containing:
            - id: The card's ID as a string.
            - vector: A dictionary with a "dense" key mapping to the dense embedding vector.
            - payload: A JSON-serializable dictionary of the card's information.

    Raises:
        ValueError: If the card's `llm_summary` attribute is None.
    """
    if card.llm_summary is None:
        raise ValueError("Card must have a summary to be embedded")
    dense_vector = dense_embed(card.llm_summary)

    card_info = card_to_info(card)
    return qm.PointStruct(
        id=str(card.id),
        vector={"dense": dense_vector},
        payload=card_info.model_dump(mode="json"),
    )
