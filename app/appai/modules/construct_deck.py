from typing import Optional
from uuid import UUID

import logfire
from appcards.models.deck import Deck
from beartype import beartype
from pydantic import BaseModel, Field

from appai.services.agents.deck_constructor import run_deck_constructor_agent


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
    deck_description: str, deck_id: Optional[UUID] = None, available_set_codes: Optional[set[str]] = None
) -> DeckConstructorResults:
    if deck_id is not None:
        logfire.info(f"Using provided deck ID: {deck_id}")
        deck = await Deck.objects.aget(id=deck_id)
    else:
        deck = await Deck.objects.acreate(name="New Deck")
        logfire.info(f"Constructing new deck, with ID: {deck.id}")
    response = await run_deck_constructor_agent(
        deck_id=deck.id, deck_description=deck_description, available_set_codes=available_set_codes
    )
    return DeckConstructorResults(
        deck_id=deck.id, deck_summary=response.summary, deck_short_summary=response.short_summary
    )
