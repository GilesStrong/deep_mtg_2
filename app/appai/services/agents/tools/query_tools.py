from uuid import UUID

from appcards.constants.storage import CARD_COLLECTION_NAME
from appcards.models import Card
from appcards.models.deck import DeckCard
from appcards.modules.card_info import CardInfo, card_to_info
from appsearch.services.qdrant.search import run_query_from_dsl
from appsearch.services.qdrant.search_dsl import Filter, MatchAnyCondition, Query
from asgiref.sync import sync_to_async
from beartype import beartype
from pydantic import BaseModel, Field
from pydantic_ai import RunContext

from appai.services.agents.deps import DeckBuildingDeps
from appai.services.agents.filter_constructor import filter_constructor

MAX_SEARCH_RESULTS = 25


class SearchResults(BaseModel):
    cards: list[CardInfo] = Field(description="The list of cards matching the search query, with their details.")
    filter_used: Filter = Field(
        description="The filter that was applied to the search, including any conditions that were automatically constructed based on the query and the current deck state."
    )
    max_results: int = Field(
        description="The maximum number of results that were requested to be returned, which may be less than the actual number of results found."
    )


# TODO: Make the main agent be able to specify the filter, and/or split the filter query and the vector-search query
@beartype
async def search_for_cards(
    ctx: RunContext[DeckBuildingDeps], query: str, search_with_advanced_filter: bool = True, max_results: int = 10
) -> SearchResults:
    """
    Searches for cards matching a query.
    The search will be performed using a vector search between the query and the card embeddings, which are based on automatically generated summaries of the cards.

    Optionally, an advanced filter can be automatically constructed from the query and applied to the search.
    The filter will be constructed based on the query, and can be used to narrow down the search results based on:
    - Card types
    - Colors
    - Power and toughness
    - Keywords
    - Cost

    Additionally, a basic filter will be constructed based on the current state of the deck:
    - Ignore cards that are already in the deck
    - Ignore cards that are not legal in the format of the deck

    The card summaries used for the vector search are generated to include:
    - The strengths and weaknesses of the card
    - The typical uses of the card
    - The synergies of the card with other cards
    - The role of the card in different archetypes and strategies

    Therefore the query can be a natural language description of the type of card the user is looking for, and the search will return cards that match that description, even if the query does not include specific details about the card.

    Be aware that the results of the search are NOT added to the deck. Use the appropriate tool to add cards to the deck after retrieving them with this search tool.

    Args:
        query (str): The search query to use.
        search_with_advanced_filter (bool): Whether to construct and apply a filter based on interpreted query.
        max_results (int): The maximum number of results to return, subject to a maximum limit.

    Returns:
        SearchResults: The search results containing the matching cards, the original query, and the filter used.
    """
    if max_results > MAX_SEARCH_RESULTS:
        max_results = MAX_SEARCH_RESULTS

    # Build filters
    existing_card_ids: list[UUID] = await sync_to_async(list)(  # type: ignore [call-arg]
        DeckCard.objects.filter(deck_id=ctx.deps.deck_id).values_list("card__id", flat=True)
    )

    basic_filter = Filter(
        must=[
            MatchAnyCondition(key="set_codes", any=list(ctx.deps.available_set_codes)),
        ],
        must_not=[
            MatchAnyCondition(key="id", any=[str(card_id) for card_id in existing_card_ids]),
        ]
        if len(existing_card_ids) > 0
        else [],
    )

    if search_with_advanced_filter:
        advanced_filter = await filter_constructor(query)
        combined_filter = Filter(
            min_should_count=advanced_filter.min_should_count,
            should=advanced_filter.should,
            must=basic_filter.must + advanced_filter.must,
            must_not=basic_filter.must_not + advanced_filter.must_not,
        )
    else:
        combined_filter = basic_filter

    # Run search
    found_cards = await sync_to_async(run_query_from_dsl)(
        Query(collection_name=CARD_COLLECTION_NAME, query_string=query, filter=combined_filter, limit=max_results),
    )

    # Convert results to CardInfo
    card_infos = []
    for point in found_cards:
        try:
            card = await Card.objects.aget(id=point.id)
            card_infos.append(await sync_to_async(card_to_info)(card))
        except Card.DoesNotExist:
            continue
    return SearchResults(cards=card_infos, filter_used=combined_filter, max_results=max_results)
