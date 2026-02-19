from uuid import UUID

from appcards.models.deck import Deck
from beartype import beartype
from pydantic import BaseModel, Field

from appai.services.agents.deck_constructor import run_deck_constructor_agent


class DeckConstructorResults(BaseModel):
    deck_id: UUID = Field(..., description="The ID of the constructed deck")
    deck_summary: str = Field(
        ..., description="A summary of the constructed deck, including its theme, strategy, and key cards"
    )


@beartype
async def construct_deck(deck_description: str) -> DeckConstructorResults:
    deck = Deck(name="New Deck")
    deck.save()
    response = await run_deck_constructor_agent(deck.id, deck_description)
    return DeckConstructorResults(deck_id=deck.id, deck_summary=response)
