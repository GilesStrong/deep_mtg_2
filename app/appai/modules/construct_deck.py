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

from typing import Optional
from uuid import UUID

import logfire
from appcards.models.deck import Deck
from appcore.modules.beartype import beartype
from pydantic import BaseModel, Field

from appai.services.graphs.deck_construction import construct_deck as construct_deck_graph


class DeckConstructorResults(BaseModel):
    deck_id: UUID = Field(..., description="The ID of the constructed deck")
    deck_summary: str = Field(
        ..., description="A summary of the constructed deck, including its theme, strategy, and key cards"
    )
    deck_short_summary: str = Field(
        ..., description="A short summary of the constructed deck, suitable for display in a list of decks"
    )


@beartype
async def construct_deck(
    *,
    deck_description: str,
    user_id: UUID,
    build_task_id: UUID,
    deck_id: Optional[UUID] = None,
    available_set_codes: Optional[set[str]] = None,
) -> None:
    """
    Constructs or updates a Magic: The Gathering deck based on a given description.

    This asynchronous function either creates a new deck or updates an existing one
    by running a deck constructor agent. It manages generation history to maintain
    context while limiting memory usage.

    Args:
        deck_description (str): A natural language description of the desired deck,
            used to guide the deck construction process.
        user_id (UUID): The unique identifier of the user creating or updating the deck.
        build_task_id (UUID): The unique identifier of the build task associated with this deck construction.
        deck_id (Optional[UUID]): If provided, the function will update the existing
            deck with this ID. If None, a new deck will be created. Defaults to None.
        available_set_codes (Optional[set[str]]): A set of MTG set codes to restrict
            card selection to specific sets. If None, the current standard-legal sets are considered.
            Defaults to None.

    Raises:
        Deck.DoesNotExist: If a deck_id is provided but no matching deck is found
            in the database.

    Notes:
        - Generation history is capped at 5 entries to manage context size.
        When exceeded, it retains the first entry and the 4 most recent entries.
        - If no generation history exists on the deck, an empty list is used.
    """
    # If deck_id is provided, we will update that deck. Otherwise, we will create a new deck.
    if deck_id is not None:
        logfire.info(f"Using provided deck ID: {deck_id}")
        deck = await Deck.objects.aget(id=deck_id)
    else:
        deck = await Deck.objects.acreate(name="New Deck", user_id=user_id)
        logfire.info(f"Constructing new deck, with ID: {deck.id}")

    # Run deck build
    generation_history = deck.generation_history if deck.generation_history else []
    if len(generation_history) > 5:
        generation_history = (
            generation_history[:1] + generation_history[-4:]
        )  # Always keep the first entry, and the most recent 4 entries
    await construct_deck_graph(
        deck_id=deck.id,
        deck_description=deck_description,
        generation_history=generation_history,
        available_set_codes=available_set_codes,
        build_task_id=build_task_id,
    )
