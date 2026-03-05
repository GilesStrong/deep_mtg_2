from dataclasses import dataclass

import logfire
from appcards.constants.storage import CARD_COLLECTION_NAME
from appcards.models.card import Card
from appcards.models.deck import DeckCard
from appcore.modules.beartype import beartype
from appsearch.services.qdrant.search import run_query_from_dsl
from appsearch.services.qdrant.search_dsl import Filter, Query
from asgiref.sync import sync_to_async
from django.db import transaction
from pydantic import BaseModel, ConfigDict, Field
from pydantic_graph import BaseNode, End, Graph, GraphRunContext

from appai.services.agents.deck_constructor import (
    run_card_replacement_agent,
)

MAX_TOP_K_REPLACEMENT_CANDIDATES = 5


class ReplacementDeps(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    deck_strategy: str = Field(
        ...,
        description="Summary of the deck and its strategy",
    )
    card_to_replace: DeckCard = Field(..., description="The card in the deck that is being considered for replacement")


@dataclass
class AddReplacements(BaseNode[None, ReplacementDeps, None]):
    """
    A graph node that adds replacement cards to a given card and persists the changes.

    This node iterates over a list of replacement cards and associates each one
    with the card designated for replacement. After all replacements have been
    added, it asynchronously saves the updated card to the database.

    Attributes:
        replacement_cards (list[Card]): A list of Card instances to be added
            as replacements for the target card.

    Args:
        ctx (GraphRunContext[None, ReplacementDeps]): The graph run context
            containing the dependencies, including the card to be replaced
            (`ctx.deps.card_to_replace`).

    Returns:
        End[None]: Signals the end of the graph execution with no output value.
    """

    replacement_cards: list[Card]

    async def run(self, ctx: GraphRunContext[None, ReplacementDeps]) -> End[None]:
        with transaction.atomic():
            ctx.deps.card_to_replace.replacement_cards.clear()
            for replacement_card in self.replacement_cards:
                await ctx.deps.card_to_replace.replacement_cards.aadd(replacement_card)
            await ctx.deps.card_to_replace.asave(update_fields=['replacement_cards'])
        return End(None)


@dataclass
class FilterReplacements(BaseNode[None, ReplacementDeps, None]):
    """
    A graph node that filters replacement card candidates using an AI agent.

    This node takes a list of potential replacement cards and runs them through
    a card replacement agent to determine which candidates are valid replacements
    based on the deck strategy and the card being replaced.

    Attributes:
        replacement_candidates (list[Card]): List of potential replacement cards to be filtered.

    Args:
        ctx (GraphRunContext[None, ReplacementDeps]): The graph run context containing:
            - deps.deck_strategy (str): The strategy of the deck being modified.
            - deps.card_to_replace (Card): The card that needs to be replaced.

    Returns:
        AddReplacements: If valid replacements are found, returns an AddReplacements node
            containing the filtered list of valid replacement cards.
        End[None]: If no valid replacements are found after filtering, logs a warning
            and terminates the graph execution.
    """

    replacement_candidates: list[Card]

    async def run(self, ctx: GraphRunContext[None, ReplacementDeps]) -> AddReplacements | End[None]:
        filtered_candidate_ids = await run_card_replacement_agent(
            deck_strategy=ctx.deps.deck_strategy,
            card_to_replace=ctx.deps.card_to_replace,
            potential_replacements=self.replacement_candidates,
        )
        if len(filtered_candidate_ids) == 0:
            logfire.warning(
                f"No valid replacements found for card {ctx.deps.card_to_replace.card.name} with strategy {ctx.deps.deck_strategy} among candidates {[card.name for card in self.replacement_candidates]}"
            )
            return End(None)
        filtered_candidates = [card for card in self.replacement_candidates if card.id in filtered_candidate_ids]
        return AddReplacements(replacement_cards=filtered_candidates)


@dataclass
class SearchForReplacements(BaseNode[None, ReplacementDeps, None]):
    """
    A graph node that searches for potential replacement cards using vector similarity search.

    This node queries a card collection using the LLM summary of the card to be replaced
    as the search query, applying the provided filter and exclusion list to narrow down
    candidates. Retrieved card IDs are then resolved to Card model instances.

    Attributes:
        card_filter (Filter): The filter criteria to apply during the vector search query.
        exclude_ids (list[str]): A list of card IDs to exclude from the search results.

    Args:
        ctx (GraphRunContext[None, ReplacementDeps]): The graph run context containing
            the dependencies, including the card to be replaced.

    Returns:
        FilterReplacements: A node containing the list of replacement candidate cards,
            if one or more candidates are found.
        End[None]: Terminates the graph with no result if no replacement candidates
            are found after resolving card IDs from the search results.
    """

    card_filter: Filter
    exclude_ids: list[str]

    async def run(self, ctx: GraphRunContext[None, ReplacementDeps]) -> FilterReplacements | End[None]:
        found_cards = await sync_to_async(run_query_from_dsl)(
            Query(
                collection_name=CARD_COLLECTION_NAME,
                query_string=ctx.deps.card_to_replace.card.llm_summary,
                filter=self.card_filter,
                limit=MAX_TOP_K_REPLACEMENT_CANDIDATES,
            ),
            exclude_ids=self.exclude_ids,
        )
        replacement_canditated: list[Card] = []
        for point in found_cards:
            try:
                card = await Card.objects.aget(id=point.id)
                replacement_canditated.append(card)
            except Card.DoesNotExist:
                continue
        if len(replacement_canditated) == 0:
            logfire.warning(
                f"No replacement candidates found for card {ctx.deps.card_to_replace.card.name} with filter {self.card_filter}"
            )
            return End(None)

        return FilterReplacements(replacement_candidates=replacement_canditated)


@beartype
async def replace_card(
    deck_strategy: str,
    deck_card_to_replace: DeckCard,
    card_filter: Filter,
    exclude_ids: list[str],
) -> None:
    """
    Asynchronously finds and replaces a card in a deck using a graph-based workflow.

    This function initializes a replacement dependency context and runs a graph-based
    pipeline to search for, filter, and add replacement cards to a deck.

    Args:
        deck_strategy (str): The strategy or theme of the deck to guide the replacement search.
        deck_card_to_replace (DeckCard): The card instance in the deck that needs to be replaced.
        card_filter (Filter): Filtering criteria to apply when searching for replacement cards.
        exclude_ids (list[str]): A list of card IDs to exclude from the replacement search results.

    Workflow:
        1. SearchForReplacements: Searches for potential replacement cards based on the
           provided filter and exclusion list.
        2. FilterReplacements: Filters the found replacements according to the deck strategy
           and other criteria.
        3. AddReplacements: Adds the most suitable replacement card to the deck.
    """
    deps = ReplacementDeps(
        deck_strategy=deck_strategy,
        card_to_replace=deck_card_to_replace,
    )

    replacement_graph: Graph[None, ReplacementDeps] = Graph(
        nodes=[
            SearchForReplacements,
            FilterReplacements,
            AddReplacements,
        ]
    )

    await replacement_graph.run(SearchForReplacements(card_filter=card_filter, exclude_ids=exclude_ids), deps=deps)
