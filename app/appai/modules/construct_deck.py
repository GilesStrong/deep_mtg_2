from appcards.models.deck import Deck
from beartype import beartype

from appai.services.agents.deck_constructor import construct_deck


@beartype
async def _construct_deck(deck_description: str) -> None:
    deck = Deck(name="New Deck")
    deck.save()
    await construct_deck(deck.id, deck_description)
