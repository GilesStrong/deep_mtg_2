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

from datetime import datetime
from uuid import UUID

from appcards.constants.storage import CARD_COLLECTION_NAME, THEME_COLLECTION_NAME
from appcards.models.card import Card
from appcards.models.deck import DeckCard
from appcards.modules.card_info import CardInfo, card_to_info
from appcore.modules.beartype import beartype
from appsearch.services.qdrant.search import run_query_from_dsl
from appsearch.services.qdrant.search_dsl import Filter, MatchAnyCondition, Query
from asgiref.sync import sync_to_async
from django.db.models import F
from pydantic import BaseModel, Field
from pydantic_ai import RunContext

from appai.models.deck_build import DeckBuildTask
from appai.services.agents.deps import DeckBuildingDeps
from appai.services.agents.filter_constructor import filter_constructor

MAX_SEARCH_RESULTS = 25


class CardSearchResults(BaseModel):
    cards: list[CardInfo] = Field(description="The list of cards matching the search query, with their details.")
    max_results: int = Field(
        description="The maximum number of results that were requested to be returned, which may be less than the actual number of results found."
    )


# TODO: Make the main agent be able to specify the filter, and/or split the filter query and the vector-search query
@beartype
async def search_for_cards(
    ctx: RunContext[DeckBuildingDeps],
    card_description: str,
    search_with_advanced_filter: bool = True,
    max_results: int = 10,
) -> CardSearchResults:
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
        card_description (str): The description of the card to search for. Do not query just keywords, instead provide a natural language description of the type of card you are looking for, and how it should function in-game.
            Include also any details that you think are relevant to the card, and the kind of deck it should fit into.
        search_with_advanced_filter (bool): Whether to construct and apply a filter based on interpreted query.
        max_results (int): The maximum number of results to return, subject to a maximum limit.

    Returns:
        CardSearchResults: The search results containing the matching cards and the maximum number of results that were requested.
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
    )

    if search_with_advanced_filter:
        advanced_filter = await filter_constructor(card_description)
        combined_filter = Filter(
            min_should_count=advanced_filter.min_should_count,
            should=advanced_filter.should,
            must=basic_filter.must + advanced_filter.must,
            must_not=basic_filter.must_not + advanced_filter.must_not,
        )
    else:
        combined_filter = basic_filter

    exclude_ids: list[str] | None
    if len(existing_card_ids) > 0:
        exclude_ids = [str(card_id) for card_id in existing_card_ids]
    else:
        exclude_ids = None

    # Run search
    found_cards = await sync_to_async(run_query_from_dsl)(
        Query(
            collection_name=CARD_COLLECTION_NAME,
            query_string=card_description,
            filter=combined_filter,
            limit=max_results,
        ),
        exclude_ids=exclude_ids,
    )

    # Convert results to CardInfo
    card_infos = []
    for point in found_cards:
        try:
            card = await Card.objects.aget(id=point.id)
            card_infos.append(await sync_to_async(card_to_info)(card))
        except Card.DoesNotExist:
            continue

    await DeckBuildTask.objects.filter(id=ctx.deps.build_task_id).aupdate(n_searches=F("n_searches") + 1)
    return CardSearchResults(cards=card_infos, max_results=max_results)


class Theme(BaseModel):
    description: str = Field(..., description="A description of the theme.")
    days_since: int = Field(..., description="The number of days since this theme was used.")


class NewTheme(BaseModel):
    description: str = Field(..., description="A description of the new theme.", min_length=20, max_length=255)


@beartype
async def find_similar_themes(proposed_theme: NewTheme) -> list[Theme]:
    """
    Searches for deck themes similar to a proposed theme.

    Args:
        proposed_theme (NewTheme): The theme query you are considering.

    Returns:
        list[Theme]: A list of previously run deck themes that are similar to the search query, along with the number of days since each theme was last used.
    """

    # Run search
    found_themes = await sync_to_async(run_query_from_dsl)(
        Query(collection_name=THEME_COLLECTION_NAME, query_string=proposed_theme.description, filter=None, limit=5)
    )
    themes = []
    for point in found_themes:
        if (
            point.score < 0.5
            or point.payload is None
            or "description" not in point.payload
            or "date" not in point.payload
        ):
            continue
        days_since = (datetime.now() - datetime.fromisoformat(point.payload["date"])).days
        themes.append(Theme(description=point.payload["description"], days_since=days_since))
    return themes
