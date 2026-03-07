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
