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

from uuid import UUID

import logfire
import qdrant_client.http.models as qm
from appcards.constants.cards import CURRENT_STANDARD_SET_CODES
from appcards.models.card import Card
from appcards.modules.card_info import card_to_info
from appcards.modules.card_validation import CardValidationError, check_related_card_uuids
from appsearch.services.qdrant.client import QDRANT_CLIENT
from appsearch.services.qdrant.upsert import upsert_documents
from asgiref.sync import sync_to_async
from django.db import transaction
from pydantic_ai import Agent, ModelRetry

from appai.constants.llm_models import TOOL_MODEL_BASIC
from appai.constants.storage import MEMORY_COLLECTION_NAME
from appai.dataclasses.memory import ExistingMemory, Memory
from appai.models.memory import Memory as PGMemory
from appai.modules.dense_embedding import dense_embed


def update_memories(existing_memories: list[ExistingMemory], new_memories: list[Memory]) -> None:
    """
    Updates the memories in the database by deleting the existing memories and inserting the new memories.

    Args:
        existing_memories (list[ExistingMemory]): The list of existing memories to be deleted.
        new_memories (list[Memory]): The list of new memories to be inserted.

    Returns:
        None: This function does not return anything. It performs database operations to update the memories.
    """
    with transaction.atomic():
        # Delete existing memories
        PGMemory.objects.filter(id__in=[memory.id for memory in existing_memories]).delete()

        # Insert new memories
        new_pg_memories: list[PGMemory] = []
        related_card_uuids_per_memory: list[list[UUID]] = []
        for memory in new_memories:
            related_card_uuids = sorted(memory.related_card_uuids)

            pg_memory = PGMemory(
                name=memory.name,
                text=memory.text,
            )
            new_pg_memories.append(pg_memory)
            related_card_uuids_per_memory.append(related_card_uuids)
        persisted_pg_memories = PGMemory.objects.bulk_create(new_pg_memories)

        # Add related cards after bulk_create so the instances have PKs
        for pg_memory, related_card_uuids in zip(persisted_pg_memories, related_card_uuids_per_memory, strict=True):
            if len(related_card_uuids) > 0:
                pg_memory.related_cards.add(*related_card_uuids)

    # Delete old memories from Qdrant
    QDRANT_CLIENT.delete(
        collection_name=MEMORY_COLLECTION_NAME, points_selector=[str(memory.id) for memory in existing_memories]
    )

    # Upsert new memories into Qdrant
    new_qdrant_points: list[qm.PointStruct] = []
    for pg_memory in persisted_pg_memories:
        embedding = dense_embed(pg_memory.text)
        str_related_card_uuids = sorted(str(card.id) for card in pg_memory.related_cards.all())
        point = qm.PointStruct(
            id=str(pg_memory.id),
            vector={'dense': embedding},
            payload={
                "name": pg_memory.name,
                "text": pg_memory.text,
                "related_card_uuids": str_related_card_uuids,
                "created_at": pg_memory.created_at.isoformat(),
            },
        )
        new_qdrant_points.append(point)
    upsert_documents(MEMORY_COLLECTION_NAME, points=new_qdrant_points)


MEMORY_MAINTENANCE_PROMPT = """
# Overview
You are a memory-maintenance agent for a Magic: The Gathering deck-building assistant.
The assistant has a long-term memory system where it stores "memories" that contain information about the deck being built, specific cards, strategies, and other relevant details that the main agent wants to remember for future reference.
However, over time duplicate memories can build up, and others can become obsolete as the new sets are released or retired from Standard.
Your task is to maintain the memory system by taking clusters of potentially related memories and using them to create a set of replacement memories that consolidate the key information in the cluster, while removing any redundant or obsolete details.

# Input
You will receive a cluster of related memories as input. Each memory will have a name, text content, a creation date, and a list of related cards.
Additionally, you will be provided with the current legal set codes in Standard, which may be useful for determining if any memories are obsolete.
Treat these set codes as the definitive source of truth for what is currently in Standard, and do not rely on your knowledge of MTG for determining which cards are in Standard or not.

# Instructions
Read the incoming memories carefully and identify which:
- Memories are related to each other and should be consolidated together.
- Details in the memories are redundant and can be removed without losing important information.
- Details are obsolete and should be removed because they are no longer relevant due to changes in the Standard format or other factors.

Based on your analysis, create a new set of memories that consolidates the key information from the input cluster, while removing any redundant or obsolete details.
The old memories will be deleted and replaced by the new ones you return, so make sure to include all important information in the new memories. Do Not rely on the old memories still being available for reference.

The memories are being saved for the benefit of future agents.
Therefore focus on the details that are most likely to be useful for future reference, rather than details that are overly specific to the current context. 
Identify any cards that are related to the memory, and include their UUIDs in the related_card_uuids fields.

Do not include any information about cards that are no longer in Standard, however you may include general descriptions of the card's role or strategy if that information is still relevant, e.g. "a strong removal spell" or "a key card in a ramp strategy", without naming the card or mentioning specific details that would only be relevant to a specific card that is no longer in Standard.
Remember that a card can have multiple printings, some of which may still be in Standard while others are not: a card is still Standard legal if at least one of its printings belongs to a currently legal set.
Do not rely on the creation date of the memories to determine obsolescence, as some older memories may still contain relevant information, and some newer memories may already be obsolete if they reference cards that are no longer in Standard.

# Output
Return a list of new memories that should replace the input cluster of memories.
You cannot output more memories than the number of input memories.
You must output at least one memory.
Remember that these new memories will completely replace the old memories, so make sure to properly consolidate all important information from the old memories into the new ones.
"""


async def maintain_memories(clustered_memories: list[ExistingMemory]) -> int:
    """
    Passes a cluster of memories into an Agent which can combine them, delete them, or otherwise alter them.
    Old memories are deleted and replaced by the new ones returned by the Agent.

    Args:
        clustered_memories (list[ExistingMemory]): A list of ExistingMemory objects that are related to each other and should be processed together for maintenance.

    Returns:
        int: The number of new memories that were created to replace the old clustered memories.
    """

    agent = Agent(
        model=TOOL_MODEL_BASIC,
        name="Memory Maintenance Agent",
        system_prompt=MEMORY_MAINTENANCE_PROMPT,
        model_settings={'thinking': "high"},
        instrument=True,
        output_type=list[Memory],
        retries=10,
        output_retries=10,
    )

    @agent.output_validator
    async def validate_memory_output(output: list[Memory]) -> list[Memory]:
        """
        Validates the output of the memory writing agent.

        Args:
            output (list[Memory]): The output from the memory writing agent.

        Returns:
            list[Memory]: The validated memory output

        Raises:
            ModelRetry: If the output is invalid, a ModelRetry exception is raised to trigger a retry of the output.
        """

        if len(output) > len(clustered_memories):
            logfire.warning(
                "Memory writing agent produced more memories than the input cluster, which is not allowed.",
                output_count=len(output),
                input_count=len(clustered_memories),
            )
            raise ModelRetry(
                f"Too many memories produced: {len(output)}. Maximum allowed is {len(clustered_memories)}."
            )
        if len(output) == 0:
            logfire.warning(
                "Memory writing agent produced no memories, which is not allowed. At least one memory must be produced.",
            )
            raise ModelRetry("No memories produced. At least one memory must be produced.")

        for memory in output:
            try:
                await check_related_card_uuids(memory.related_card_uuids)
            except CardValidationError as e:
                logfire.warning("Memory writing agent produced invalid related_card_uuids.", error=str(e))
                raise ModelRetry("Invalid related_card_uuids: " + str(e))
        return output

    input_messages: list[str] = []
    input_messages.append(f"""
The current set of legal set codes in Standard is: {', '.join(CURRENT_STANDARD_SET_CODES)}.
""")
    for i, memory in enumerate(clustered_memories):
        message = f"""
Memory {i + 1}:
Name: {memory.name}
Text: {memory.text}
Created At: {memory.created_at}
Related Cards:
"""
        cards: list[Card] = await sync_to_async(list)(
            Card.objects.prefetch_related("printings").filter(id__in=memory.related_card_uuids)  # type: ignore [call-arg]
        )
        for card in cards:
            card_info = card_to_info(card)
            message += f"""
## Card Name: {card_info.name}, ID: {card_info.id}
{card_info.model_dump_json(exclude={"id", "name"})}
"""
        input_messages.append(message)

    response = await agent.run(input_messages)
    output = response.output
    new_memories = output
    await sync_to_async(update_memories)(clustered_memories, new_memories)
    return len(new_memories)
