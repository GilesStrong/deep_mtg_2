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
from appcards.models.card import Card
from appcore.modules.beartype import beartype
from appsearch.services.qdrant.client import QDRANT_CLIENT
from appsearch.services.qdrant.search import run_query_from_dsl
from appsearch.services.qdrant.search_dsl import Filter, MatchAnyCondition, Query
from appsearch.services.qdrant.upsert import create_collection_if_not_exists, upsert_documents
from asgiref.sync import sync_to_async
from pydantic import BaseModel, Field, field_validator
from pydantic_ai import Agent

from appai.constants.llm_models import TOOL_MODEL_BASIC
from appai.constants.storage import MEMORY_COLLECTION_NAME
from appai.models.memory import Memory as PGMemory
from appai.modules.dense_embedding import dense_embed

MAX_SEARCH_RESULTS = 5
MIN_RELEVANCE_SCORE = 0.5


def _validate_related_card_uuids(v: list[UUID]) -> list[UUID]:
    existing_card_uuids = set(Card.objects.filter(uuid__in=v).values_list("uuid", flat=True))
    non_existing_uuids = set(v) - existing_card_uuids
    if non_existing_uuids:
        raise ValueError(
            f"The following related_card_uuids do not correspond to existing cards: {', '.join(str(uuid) for uuid in non_existing_uuids)}"
        )
    return v


class Memory(BaseModel):
    name: str = Field(
        max_length=64, description="The name of the memory, which can be used to reference it in future queries."
    )
    text: str = Field(description="The content of the memory, which can be any text that the agent wants to remember.")
    related_card_uuids: list[UUID] = Field(
        default_factory=list,
        max_length=10,
        description="A list of UUIDs of cards that are related to this memory, which can be used to link the memory to specific cards and retrieve it later based on those cards. Up to 10 related card UUIDs can be included.",
    )

    @field_validator("related_card_uuids", mode="after")
    @classmethod
    def validate_related_card_uuids(cls, v: list[UUID]) -> list[UUID]:
        return _validate_related_card_uuids(v)


MEMORY_WRITING_AGENT_PROMPT = """
# Overview
You are a memory-writing agent for a Magic: The Gathering deck-building assistant.
Your task is to take unstructured text input from the main agent, which may contain important information that the main agent wants to remember for later use, and convert it into a structured memory format that can be easily stored and retrieved.

# Input
You will receive a message from the main agent containing the text that you need to convert into a memory.
The text may contain information about the deck being built, specific cards, strategies, or any other relevant details that the main agent wants to remember.

# Instructions
Read the input text carefully and identify the key information that should be remembered.
The current main agent will not need the memory again, rather it is being saved for the benefit of future agents.
Therefore focus on the details that are most likely to be useful for future reference, rather than details that are overly specific to the current context. 
Identify any cards that are related to the memory, and include their UUIDs in the related_card_uuids field. These should be mentioned in the text sent by the main agent.

## Refusals
You may refuse to write the memory by returning None, if you are confident that the information is not worth remembering for future reference.
Grounds for refusal are:
- The memory is not relevant to Magic: The Gathering.
- The memory focusses on the user's personal preferences or feelings rather than on objective insights that could be useful for future reference.
- The memory is too specific to the current context and is unlikely to be useful for future reference.
Memories will be shared across multiple different users and agents, so do not include any personal information or details that are specific to the current user or agent.
Use you own judgement to determine whether the information is worth remembering for future reference, and do not be afraid to refuse to write a memory if you think it is not worth remembering.
"""


# TODO: Add memory clearing task to remove old memories that are no longer relevant
@beartype
async def write_memory(content: str) -> None:
    """
    Tool for recroding memories that you think will be useful for future reference.
    The memories recorded here are not necessarily beneficial for you, however they may be beneficial for future agents.
    Memories can be, e.g.:
    - Synergies that you discover between cards that you think will be useful to remember later
    - Deck building strategies that you think will be useful to remember later
    - Meta cards/insights about the current state of the game that you think will be useful to remember later

    Do not record everything, instead focus on recording the most important insights that you think will be useful for future reference.
    Use your own judgement to determine what information is worth remembering, and what information is not worth remembering.
    You can also include in the memory the UUIDs of any cards that are related to the memory, which will allow you to retrieve the memory later based on those cards.

    Args:
        content (str): The unstructured memory content that you want to remember.
            A subagent will process this content and convert it into a structured memory format, which will then be stored in the database and the vector search index for future retrieval.

    Returns:
        None: This tool does not return any output, it simply records the memory for future reference.
    """
    await sync_to_async(create_collection_if_not_exists)(MEMORY_COLLECTION_NAME)

    # Subagent to convert the content into a structured memory format
    agent = Agent(
        model=TOOL_MODEL_BASIC,
        system_prompt=MEMORY_WRITING_AGENT_PROMPT,
        output_type=Memory | None,  # type: ignore [arg-type]
        retries=10,
        output_retries=10,
        instrument=True,
    )

    response = await agent.run(content)
    output = response.output
    if output is None:
        logfire.info("Memory writing agent refused to write a memory based on the provided content.", content=content)
        return

    # Persist the memory to the database
    memory = await PGMemory.objects.acreate(
        name=output.name,
        text=output.text,
        related_card_uuids=[str(uuid) for uuid in output.related_card_uuids],
    )

    # Upsert the memory to the vector database
    embedding = dense_embed(output.text)
    point = qm.PointStruct(
        id=str(memory.id),
        vector=embedding,
        payload={
            "name": output.name,
            "text": output.text,
            "related_card_uuids": [str(uuid) for uuid in output.related_card_uuids],
            "created_at": memory.created_at.isoformat(),
        },
    )
    await sync_to_async(upsert_documents)(collection_name=MEMORY_COLLECTION_NAME, points=[point])
    logfire.info(
        "Memory successfully recorded and upserted to vector database.",
        name=memory.name,
        text=memory.text,
        related_card_uuids=memory.related_card_uuids,
    )


class MemorySearchResult(BaseModel):
    memories: list[Memory] = Field(description="The list of memories that were found based on the search query.")
    total_memories: int = Field(
        ge=0,
        description="The total number of memories currently stored in the database, which can be useful for understanding the scale of the memory database and for debugging purposes.",
    )


@beartype
async def semantic_memory_search(query: str) -> MemorySearchResult:
    """
    Semantic search for memories based on a natural language query.
    The search will be performed using a vector search between the query and the memory embeddings, which are based on the text content of the memories.

    Args:
        query (str): The natural language query to search for

    Returns:
        MemorySearchResult: An object containing upto five relevant memories based on the search query.
    """
    await sync_to_async(create_collection_if_not_exists)(MEMORY_COLLECTION_NAME)
    total_memories = await sync_to_async(QDRANT_CLIENT.count)(collection_name=MEMORY_COLLECTION_NAME)
    if total_memories.count == 0:
        return MemorySearchResult(memories=[], total_memories=0)

    # Run search
    found_memories = await sync_to_async(run_query_from_dsl)(
        Query(
            collection_name=MEMORY_COLLECTION_NAME,
            query_string=query,
            filter=None,
            limit=MAX_SEARCH_RESULTS,
        ),
        score_threshold=MIN_RELEVANCE_SCORE,
    )
    output: list[Memory] = []
    for item in found_memories:
        payload = item.payload
        if payload is None:
            continue
        output.append(
            Memory(
                name=payload["name"],
                text=payload["text"],
                related_card_uuids=[UUID(uuid) for uuid in payload["related_card_uuids"]],
            )
        )
    return MemorySearchResult(memories=output, total_memories=total_memories.count)


@beartype
async def card_memory_search(card_uuids: list[UUID]) -> MemorySearchResult:
    """
    Search for memories that are related to specific cards, based on the related_card_uuids field of the memories.

    Args:
        card_uuids (list[UUID]): A list of UUIDs of the cards to search for related memories.

    Returns:
        MemorySearchResult: An object containing the relevant memories based on the card UUIDs.
    """
    await sync_to_async(create_collection_if_not_exists)(MEMORY_COLLECTION_NAME)
    total_memories = await sync_to_async(QDRANT_CLIENT.count)(collection_name=MEMORY_COLLECTION_NAME)
    if total_memories.count == 0:
        return MemorySearchResult(memories=[], total_memories=0)

    if not card_uuids:
        return MemorySearchResult(memories=[], total_memories=total_memories.count)

    memory_filter = Filter(
        should=[MatchAnyCondition(key="related_card_uuids", any=[str(uuid) for uuid in card_uuids])],
        min_should_count=1,
    )
    found_memories = await sync_to_async(run_query_from_dsl)(
        Query(
            collection_name=MEMORY_COLLECTION_NAME,
            query_string=None,
            filter=memory_filter,
            limit=MAX_SEARCH_RESULTS,
        ),
        score_threshold=MIN_RELEVANCE_SCORE,
    )
    output: list[Memory] = []
    for item in found_memories:
        payload = item.payload
        if payload is None:
            continue
        output.append(
            Memory(
                name=payload["name"],
                text=payload["text"],
                related_card_uuids=[UUID(uuid) for uuid in payload["related_card_uuids"]],
            )
        )
    return MemorySearchResult(memories=output, total_memories=total_memories.count)


MEMORY_SEARCH_PROMPT = """
# Overview
You are a memory-searching agent for a Magic: The Gathering deck-building assistant.
Your task is to search for relevant memories based on a natural language query, and return a summary message based on the retrieved memories.
The memories have been previously recorded from past agents, and contain valuable insights and information that can be useful for the current deck-building process.

# Input
You will receive a natural language query from the main agent, which may contain questions, requests for information, or any other relevant details that the main agent wants to find out based on the existing memories

# Instructions
Read the input query carefully and identify the key information that is being requested.
Search for relevant memories based on the input query, using both semantic search and card-related search if applicable.
Summarize the retrieved memories in a concise and informative manner, focusing on the most relevant insights that can help with the current deck-building process.
Only include information in the summary that you have retrieved from the memories, and do not include any information that is not supported by the retrieved memories.
Do NOT use your own knowledge or make assumptions that are not supported by the retrieved memories, as the main agent is specifically asking for information that has been recorded in the memory database, and not for your own general knowledge or assumptions.
Do NOT make suggestions or recommendations based on the retrieved memories: simply summarize the relevant information and let the main agent make its own decisions based on that information.
"""


class MemorySummary(BaseModel):
    summary: str = Field(description="A summary of the relevant memories that were found based on the search query.")
    related_card_uuids: list[UUID] = Field(
        default_factory=list,
        description="A list of UUIDs of cards that are related to the relevant memories, which can be used to link the summary to specific cards and retrieve it later based on those cards.",
    )

    @field_validator("related_card_uuids", mode="after")
    @classmethod
    def validate_related_card_uuids(cls, v: list[UUID]) -> list[UUID]:
        return _validate_related_card_uuids(v)


class SubagentMemorySearchResult(BaseModel):
    memory_summary: MemorySummary = Field(
        description="A summary of the relevant memories that were found based on the search query."
    )
    total_memories: int = Field(
        ge=0,
        description="The total number of memories currently stored in the database, which can be useful for understanding the scale of the memory database and for debugging purposes.",
    )


@beartype
async def subagent_memory_search(query: str) -> SubagentMemorySearchResult:
    """
    Tool for searching for relevant memories based on a natural language query, and returning a summary message based on the retrieved memories.
    The memories have been previously recorded from past agents, and contain valuable insights and information that have been deemed worth remembering for future reference.
    A subagent will process the search query, retrieve the relevant memories, and generate a summary based on those memories, which will then be returned to the main agent for use in the current deck-building process.

    Args:
        query (str): The natural language query to search for relevant memories.
    Returns:
        SubagentMemorySearchResult: The result of the memory search, including a summary of the relevant memories and the total number of memories in the database.
    """
    await sync_to_async(create_collection_if_not_exists)(MEMORY_COLLECTION_NAME)
    total_memories = await sync_to_async(QDRANT_CLIENT.count)(collection_name=MEMORY_COLLECTION_NAME)
    if total_memories.count == 0:
        return SubagentMemorySearchResult(
            memory_summary=MemorySummary(summary="No memories currently stored in the database."), total_memories=0
        )

    agent = Agent(
        model=TOOL_MODEL_BASIC,
        system_prompt=MEMORY_SEARCH_PROMPT,
        instrument=True,
        tools=[semantic_memory_search, card_memory_search],
        output_type=MemorySummary,
        retries=10,
        output_retries=10,
    )
    response = await agent.run(query)
    return SubagentMemorySearchResult(memory_summary=response.output, total_memories=total_memories.count)
