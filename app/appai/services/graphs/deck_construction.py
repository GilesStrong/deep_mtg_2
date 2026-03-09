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

import asyncio
from asyncio import Semaphore
from dataclasses import dataclass
from typing import Optional
from uuid import UUID

import logfire
from app.app_settings import APP_SETTINGS
from appcards.constants.cards import CURRENT_STANDARD_SET_CODES
from appcards.models.deck import Deck, DeckCard
from appcards.modules.deck_info import get_colors_from_deck
from appcore.modules.beartype import beartype
from appsearch.services.qdrant.search_dsl import Filter, MatchAnyCondition
from asgiref.sync import sync_to_async
from django.db.models import F
from pydantic import BaseModel, Field
from pydantic_graph import BaseNode, End, Graph, GraphRunContext
from tenacity import retry, stop_after_attempt, wait_exponential

from appai.models.deck_build import DeckBuildStatus, DeckBuildTask
from appai.services.agents.deck_constructor import run_card_classifier_agent, run_deck_constructor_agent
from appai.services.agents.deps import DeckBuildingDeps
from appai.services.graphs.replace_card import replace_card

MAX_BUILD_ATTEMPTS = 3
MAX_CONCURRENCY = 8


class DeckConstructionState(BaseModel):
    generation_history: list[str] = Field(
        default_factory=list,
        description="A history of the deck generations and modifications that have been made during this deck construction process, which can be used to inform future generations and avoid repeating the same mistakes.",
    )
    build_count: int = Field(0, description="The number of times the deck has been built or modified", ge=0)


@dataclass
class SetSwaps(BaseNode[DeckConstructionState, DeckBuildingDeps, None]):
    """
    A graph node that handles card swapping in a Magic: The Gathering deck construction pipeline.

    This node identifies cards in the deck that are not marked as 'Critical' or 'High Synergy'
    and attempts to replace them with better alternatives from the available card sets.

    The replacement process:
        1. Fetches all cards in the deck and filters out high-priority cards.
        2. Builds search filters based on the deck's color identity and available set codes.
        3. Concurrently replaces eligible cards using a semaphore-controlled async pool,
           with retry logic to handle transient failures.

    Args:
        ctx (GraphRunContext[DeckConstructionState, DeckBuildingDeps]): The graph run context
            containing the deck ID, available set codes, and deck description used for
            replacement decisions.

    Returns:
        End[None]: Signals the end of the graph execution, regardless of whether any
            replacements were made.
    """

    async def run(self, ctx: GraphRunContext[DeckConstructionState, DeckBuildingDeps]) -> End[None]:
        await DeckBuildTask.objects.filter(id=ctx.deps.build_task_id).aupdate(
            status=DeckBuildStatus.FINDING_REPLACEMENT_CARDS
        )
        # Get deck cards
        deck_cards: list[DeckCard] = await sync_to_async(list)(  # type: ignore [call-arg]
            DeckCard.objects.filter(deck_id=ctx.deps.deck_id).select_related('card', 'deck')
        )
        cards_to_replace = [
            deck_card for deck_card in deck_cards if deck_card.importance not in ["Critical", "High Synergy"]
        ]
        if len(cards_to_replace) == 0:
            logfire.info("No cards to replace in deck. Skipping replacement step.")
            return End(None)
        await DeckBuildTask.objects.filter(id=ctx.deps.build_task_id).aupdate(
            n_total_replacements=len(cards_to_replace)
        )

        # Build filters
        deck = await Deck.objects.aget(id=ctx.deps.deck_id)
        colors = await sync_to_async(get_colors_from_deck)(deck)
        must = [
            MatchAnyCondition(key="set_codes", any=list(ctx.deps.available_set_codes)),
        ]
        if colors:
            must.append(MatchAnyCondition(key="colors", any=list(colors)))
        search_filter = Filter(
            must=must,  # type: ignore [arg-type]
        )
        existing_card_ids: list[UUID] = await sync_to_async(list)(  # type: ignore [call-arg]
            DeckCard.objects.filter(deck_id=ctx.deps.deck_id).values_list("card__id", flat=True)
        )
        existing_card_str_ids = [str(card_id) for card_id in existing_card_ids]

        # run replacement
        semaphore = Semaphore(MAX_CONCURRENCY)

        @retry(
            stop=stop_after_attempt(APP_SETTINGS.DECK_BUILD_RETRY_LIMIT),
            wait=wait_exponential(multiplier=1, min=2, max=10),
        )
        async def _run_replacement_for_card(deck_card: DeckCard) -> None:
            async with semaphore:
                await replace_card(
                    deck_strategy=deck.llm_summary or ctx.deps.deck_description,
                    deck_card_to_replace=deck_card,
                    card_filter=search_filter,
                    exclude_ids=existing_card_str_ids,
                )
                await DeckBuildTask.objects.filter(id=ctx.deps.build_task_id).aupdate(
                    n_replacements=F("n_replacements") + 1
                )

        await asyncio.gather(*[_run_replacement_for_card(deck_card) for deck_card in cards_to_replace])
        return End(None)


@dataclass
class ClassifyCards(BaseNode[DeckConstructionState, DeckBuildingDeps]):
    """
    A node in the deck construction graph responsible for classifying cards in a deck.

    This node runs the card classifier agent to analyze and categorize cards based on
    the deck's description and composition.

    Args:
        ctx (GraphRunContext[DeckConstructionState, DeckBuildingDeps]): The graph
            run context containing the current state and dependencies, including
            the deck ID and deck description needed for classification.

    Returns:
        SetSwaps: Transitions the graph to the SetSwaps node after classification
            is complete.
    """

    async def run(self, ctx: GraphRunContext[DeckConstructionState, DeckBuildingDeps]) -> SetSwaps:
        await DeckBuildTask.objects.filter(id=ctx.deps.build_task_id).aupdate(
            status=DeckBuildStatus.CLASSIFYING_DECK_CARDS
        )
        await run_card_classifier_agent(deck_id=ctx.deps.deck_id, deck_description=ctx.deps.deck_description)
        return SetSwaps()


@dataclass
class ValidateDeck(BaseNode[DeckConstructionState, DeckBuildingDeps]):
    """
    Node that validates whether a deck has been successfully built.

    Checks if the deck associated with the current context is marked as valid
    in the database. If the deck is not valid, it will retry the build process
    up to MAX_BUILD_ATTEMPTS times before raising a RuntimeError.

    Returns:
        BuildDeck: If the deck is not valid and the build count is below the
            maximum number of allowed attempts.
        ClassifyCards: If the deck is valid, proceeding to the card
            classification step.

    Raises:
        RuntimeError: If the deck validation fails and the maximum number of
            build attempts (MAX_BUILD_ATTEMPTS) has been reached.
    """

    async def run(self, ctx: GraphRunContext[DeckConstructionState, DeckBuildingDeps]) -> "BuildDeck | ClassifyCards":
        is_valid = await Deck.objects.filter(id=ctx.deps.deck_id, valid=True).aexists()
        if not is_valid:
            if ctx.state.build_count >= MAX_BUILD_ATTEMPTS:
                message = f"Deck validation failed after {ctx.state.build_count} attempts. Aborting deck construction."
                logfire.error(message)
                raise RuntimeError(message)
            else:
                logfire.warning(
                    f"Deck validation failed on attempt {ctx.state.build_count}. Retrying deck construction. Deck ID: {ctx.deps.deck_id}"
                )
                return BuildDeck()
        return ClassifyCards()


@dataclass
class BuildDeck(BaseNode[DeckConstructionState, DeckBuildingDeps]):
    """
    Node responsible for constructing a Magic: The Gathering deck based on the provided context.

    This node invokes the deck constructor agent with the relevant deck information
    and tracks the number of build attempts made during the deck construction process.

    Args:
        ctx (GraphRunContext[DeckConstructionState, DeckBuildingDeps]): The graph run context
            containing the current state and dependencies required for deck construction,
            including:
            - ctx.deps.deck_id (str): The unique identifier of the deck being constructed.
            - ctx.deps.deck_description (str): A description of the desired deck.
            - ctx.deps.available_set_codes (list[str]): The list of MTG set codes available
                for card selection.
            - ctx.state.generation_history: The history of previous generation attempts.
            - ctx.state.build_count (int): Counter tracking the number of build attempts.

    Returns:
        ValidateDeck: Transitions the graph to the ValidateDeck node for deck validation.
    """

    async def run(self, ctx: GraphRunContext[DeckConstructionState, DeckBuildingDeps]) -> ValidateDeck:
        await DeckBuildTask.objects.filter(id=ctx.deps.build_task_id).aupdate(status=DeckBuildStatus.BUILDING_DECK)
        await run_deck_constructor_agent(
            deck_id=ctx.deps.deck_id,
            build_task_id=ctx.deps.build_task_id,
            deck_description=ctx.deps.deck_description,
            available_set_codes=ctx.deps.available_set_codes,
            generation_history=ctx.state.generation_history,
        )
        ctx.state.build_count += 1
        return ValidateDeck()


@beartype
async def construct_deck(
    *,
    deck_id: UUID,
    deck_description: str,
    generation_history: list[str],
    build_task_id: UUID,
    available_set_codes: Optional[set[str]] = None,
) -> None:
    """
    Asynchronously constructs a Magic: The Gathering deck based on a given description.

    This function initializes the necessary dependencies and state for deck construction,
    then runs a graph-based workflow to build, validate, classify, and finalize the deck.

    Args:
        deck_id (UUID): The unique identifier for the deck being constructed.
        deck_description (str): A textual description of the desired deck, used to guide
            the deck-building process.
        generation_history (list[str]): A list of previous generation attempts or history
            entries to inform the construction process.
        build_task_id (UUID): The unique identifier of the build task associated with this deck construction.
        available_set_codes (Optional[set[str]]): A set of MTG set codes representing the
            card sets available for deck construction. Defaults to the current Standard
            legal set codes if not provided.

    Workflow:
        The deck construction follows a graph-based pipeline consisting of the following nodes:
            1. BuildDeck: Generates the initial deck based on the description.
            2. ValidateDeck: Validates the generated deck for rule compliance.
            3. ClassifyCards: Classifies the cards within the deck.
            4. SetSwaps: Performs set-specific card swaps based on available set codes.
    """
    deps = DeckBuildingDeps(
        deck_id=deck_id,
        deck_description=deck_description,
        available_set_codes=available_set_codes or set(CURRENT_STANDARD_SET_CODES),
        build_task_id=build_task_id,
    )
    state = DeckConstructionState(build_count=0, generation_history=generation_history)

    deck_graph = Graph(
        nodes=[
            BuildDeck,
            ValidateDeck,
            ClassifyCards,
            SetSwaps,
        ]
    )

    await deck_graph.run(BuildDeck(), deps=deps, state=state)
