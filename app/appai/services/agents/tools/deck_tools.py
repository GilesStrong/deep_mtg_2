import html
import unicodedata
from uuid import UUID

from appcards.models import Card, Deck
from appcards.models.deck import DeckCard, DeckValidationResult, validate_deck_basic
from beartype import beartype
from django.db.models import Sum
from pydantic_ai import RunContext

from appai.services.agents.deps import DeckBuildingDeps


@beartype
async def rename_deck(ctx: RunContext[DeckBuildingDeps], new_name: str) -> str:
    """
    Renames a deck.

    Args:
        new_name (str): The new name for the deck.

    Returns:
        str: A message indicating the result of the operation.
    """
    if new_name.strip() == "":
        return "Deck name cannot be empty."
    try:
        deck = Deck.objects.get(id=ctx.deps.deck_id)
        deck.name = unicodedata.normalize("NFKC", html.escape(new_name))
        deck.save()
        return f"Deck renamed to '{deck.name}'."
    except Deck.DoesNotExist:
        return f"Deck with ID {ctx.deps.deck_id} does not exist."


@beartype
async def add_card_to_deck(ctx: RunContext[DeckBuildingDeps], card_id: UUID, number_to_add: int = 1) -> str:
    """
    Adds a card to a deck.

    Args:
        card_id (UUID): The ID of the card to add.
        number_to_add (int): The number of copies of the card to add.

    Returns:
        str: A message indicating the result of the operation.
    """
    try:
        deck = Deck.objects.get(id=ctx.deps.deck_id)
    except Deck.DoesNotExist:
        return f"Deck with ID {ctx.deps.deck_id} does not exist."

    try:
        card = Card.objects.get(id=card_id)
    except Card.DoesNotExist:
        return f"Card with ID {card_id} does not exist."

    deck_card, created = DeckCard.objects.get_or_create(deck=deck, card=card, defaults={'quantity': 0})
    deck_card.quantity += number_to_add
    deck_card.save()
    ctx.deps.validated = validate_deck_basic(deck).valid

    total_cards = DeckCard.objects.filter(deck=deck).aggregate(Sum('quantity'))['quantity__sum'] or 0
    return f"Added {number_to_add}x '{card.name}' to deck '{deck.name}'. Deck now has {total_cards} total cards ({deck_card.quantity}x {card.name})."


@beartype
async def remove_card_from_deck(ctx: RunContext[DeckBuildingDeps], card_id: UUID, number_to_remove: int = 1) -> str:
    """
    Removes a card from a deck.

    Args:
        card_id (UUID): The ID of the card to remove.
        number_to_remove (int): The number of copies of the card to remove.

    Returns:
        str: A message indicating the result of the operation.
    """
    try:
        deck = Deck.objects.get(id=ctx.deps.deck_id)
    except Deck.DoesNotExist:
        return f"Deck with ID {ctx.deps.deck_id} does not exist."

    try:
        card = Card.objects.get(id=card_id)
    except Card.DoesNotExist:
        return f"Card with ID {card_id} does not exist."

    try:
        deck_card = DeckCard.objects.get(deck=deck, card=card)
    except DeckCard.DoesNotExist:
        return f"Card '{card.name}' is not in deck '{deck.name}'."

    deck_card.quantity -= number_to_remove

    if deck_card.quantity <= 0:
        deck_card.delete()
        ctx.deps.validated = False
        total_cards = DeckCard.objects.filter(deck=deck).aggregate(Sum('quantity'))['quantity__sum'] or 0
        return f"Removed all copies of '{card.name}' from deck '{deck.name}'. Deck now has {total_cards} total cards."
    else:
        deck_card.save()
        ctx.deps.validated = validate_deck_basic(deck).valid
        total_cards = DeckCard.objects.filter(deck=deck).aggregate(Sum('quantity'))['quantity__sum'] or 0
        return f"Removed {number_to_remove}x '{card.name}' from deck '{deck.name}'. Deck now has {total_cards} total cards ({deck_card.quantity}x {card.name} remaining)."


@beartype
async def clear_deck(ctx: RunContext[DeckBuildingDeps]) -> str:
    """
    Clears all cards from a deck.

    Returns:
        str: A message indicating the result of the operation.
    """
    try:
        deck = Deck.objects.get(id=ctx.deps.deck_id)
    except Deck.DoesNotExist:
        return f"Deck with ID {ctx.deps.deck_id} does not exist."

    DeckCard.objects.filter(deck=deck).delete()
    ctx.deps.validated = False
    return f"All cards removed from deck '{deck.name}'."


@beartype
async def list_deck_cards(ctx: RunContext[DeckBuildingDeps]) -> str:
    """
    Lists all cards in a deck.

    Returns:
        str: A message listing all cards in the deck.
    """
    try:
        deck = Deck.objects.get(id=ctx.deps.deck_id)
        deck_cards = DeckCard.objects.filter(deck=deck).select_related('card')
        if not deck_cards.exists():
            return f"Deck '{deck.name}' is empty."
        card_list = "\n".join(
            [f"{dc.quantity}x {dc.card.name} -- {dc.card.id}: {dc.card.llm_summary}" for dc in deck_cards]
        )
        return f"Cards in deck '{deck.name}':\n{card_list}"
    except Deck.DoesNotExist:
        return f"Deck with ID {ctx.deps.deck_id} does not exist."


@beartype
async def validate_deck(ctx: RunContext[DeckBuildingDeps]) -> DeckValidationResult:
    """
    Validates a deck against basic rules (e.g. minimum 60 cards, no more than 4 copies of a card except basic lands).
    This function is intended to be used as a quick check for deck validity, and does not enforce any format-specific rules (e.g. Standard legality, Commander rules, etc.).
    It does not check for card legality based on set codes or banned/restricted lists, only the basic structural rules of deck construction.
    It also does not check for any specific card requirements, limitations, or allowances that may exist.

    Returns:
        DeckValidationResult: A message indicating whether the deck is valid or listing any issues found.
    """

    response = validate_deck_basic(ctx.deps.deck_id)
    ctx.deps.validated = response.valid
    return response
