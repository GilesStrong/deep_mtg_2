from uuid import UUID

import logfire
from appcards.models.deck import Deck
from beartype import beartype
from mistralai import Optional
from pydantic import BaseModel, Field

from appai.services.agents.deck_constructor import run_deck_constructor_agent


class DeckConstructorResults(BaseModel):
    deck_id: UUID = Field(..., description="The ID of the constructed deck")
    deck_summary: str = Field(
        ..., description="A summary of the constructed deck, including its theme, strategy, and key cards"
    )


@beartype
async def construct_deck(deck_description: str, deck_id: Optional[UUID] = None) -> DeckConstructorResults:
    if deck_id is not None:
        logfire.info(f"Using provided deck ID: {deck_id}")
        deck = await Deck.objects.aget(id=deck_id)
    else:
        deck = await Deck.objects.acreate(name="New Deck")
        logfire.info(f"Constructing new deck, with ID: {deck.id}")
    response = await run_deck_constructor_agent(deck.id, deck_description)
    return DeckConstructorResults(deck_id=deck.id, deck_summary=response)
