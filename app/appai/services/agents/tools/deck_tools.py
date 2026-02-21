import html
import unicodedata
from uuid import UUID

from appcards.models.card import Card
from appcards.models.deck import MAX_DECK_NAME_LENGTH, Deck, DeckCard, DeckValidationResult, validate_deck_basic
from asgiref.sync import sync_to_async
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
        message = "Deck name cannot be empty."
        return message
    try:
        deck = await Deck.objects.aget(id=ctx.deps.deck_id)
        new_name = unicodedata.normalize("NFKC", html.escape(new_name))
        if len(new_name) > MAX_DECK_NAME_LENGTH:
            message = f"Deck name cannot exceed {MAX_DECK_NAME_LENGTH} characters."
            return message
        deck.name = new_name
        await deck.asave()
        message = f"Deck renamed to '{deck.name}'."
        return message
    except Deck.DoesNotExist:
        message = f"Deck with ID {ctx.deps.deck_id} does not exist."
        return message


@beartype
async def add_card_to_deck(ctx: RunContext[DeckBuildingDeps], card_id: UUID, number_to_add: int = 1) -> str:
    """
    Adds a card to a deck.

    Args:
        card_id (UUID): The ID of the card to add.
        number_to_add (int): The number of copies of the card to add (positive, non-zero integer).

    Returns:
        str: A message indicating the result of the operation.
    """
    if number_to_add <= 0:
        message = "Number of copies to add must be a positive, non-zero integer."
        return message

    try:
        deck = await Deck.objects.aget(id=ctx.deps.deck_id)
    except Deck.DoesNotExist:
        message = f"Deck with ID {ctx.deps.deck_id} does not exist."
        return message

    try:
        card = await Card.objects.aget(id=card_id)
    except Card.DoesNotExist:
        message = f"Card with ID {card_id} does not exist."
        return message

    if number_to_add <= 0:
        message = "number_to_add must be a positive integer."
        return message
    deck_card, created = await DeckCard.objects.aget_or_create(deck=deck, card=card, defaults={'quantity': 0})
    deck_card.quantity += number_to_add
    await deck_card.asave()

    total_cards = await DeckCard.objects.filter(deck=deck).aaggregate(Sum('quantity'))
    total_cards = total_cards['quantity__sum'] or 0
    message = f"Added {number_to_add}x '{card.name}' to deck '{deck.name}'. Deck now has {total_cards} total cards ({deck_card.quantity}x {card.name})."
    return message


@beartype
async def remove_card_from_deck(ctx: RunContext[DeckBuildingDeps], card_id: UUID, number_to_remove: int = 1) -> str:
    """
    Removes a card from a deck.

    Args:
        card_id (UUID): The ID of the card to remove.
        number_to_remove (int): The number of copies of the card to remove (positive, non-zero integer).

    Returns:
        str: A message indicating the result of the operation.
    """
    if number_to_remove <= 0:
        message = "Number of copies to remove must be a positive, non-zero integer."
        return message

    try:
        deck = await Deck.objects.aget(id=ctx.deps.deck_id)
    except Deck.DoesNotExist:
        message = f"Deck with ID {ctx.deps.deck_id} does not exist."
        return message

    try:
        card = await Card.objects.aget(id=card_id)
    except Card.DoesNotExist:
        message = f"Card with ID {card_id} does not exist."
        return message

    try:
        deck_card = await DeckCard.objects.aget(deck=deck, card=card)
    except DeckCard.DoesNotExist:
        message = f"Card '{card.name}' is not in deck '{deck.name}'."
        return message

    deck_card.quantity -= number_to_remove

    if deck_card.quantity <= 0:
        await deck_card.adelete()
        total_cards = await DeckCard.objects.filter(deck=deck).aaggregate(Sum('quantity'))
        total_cards = total_cards['quantity__sum'] or 0
        message = (
            f"Removed all copies of '{card.name}' from deck '{deck.name}'. Deck now has {total_cards} total cards."
        )
        return message
    else:
        await deck_card.asave()
        total_cards = await DeckCard.objects.filter(deck=deck).aaggregate(Sum('quantity'))
        total_cards = total_cards['quantity__sum'] or 0
        message = f"Removed {number_to_remove}x '{card.name}' from deck '{deck.name}'. Deck now has {total_cards} total cards ({deck_card.quantity}x {card.name} remaining)."
        return message


@beartype
async def clear_deck(ctx: RunContext[DeckBuildingDeps]) -> str:
    """
    Clears all cards from a deck.

    Returns:
        str: A message indicating the result of the operation.
    """
    try:
        deck = await Deck.objects.aget(id=ctx.deps.deck_id)
    except Deck.DoesNotExist:
        message = f"Deck with ID {ctx.deps.deck_id} does not exist."
        return message

    await DeckCard.objects.filter(deck=deck).adelete()
    message = f"All cards removed from deck '{deck.name}'."
    return message


@beartype
async def list_deck_cards(ctx: RunContext[DeckBuildingDeps]) -> str:
    """
    Lists all cards in a deck.

    Returns:
        str: A message listing all cards in the deck.
    """
    try:
        deck_cards: list[DeckCard] = await sync_to_async(list)(  # type: ignore [call-arg]
            DeckCard.objects.filter(deck_id=ctx.deps.deck_id).select_related('card', 'deck')
        )

        if not deck_cards:
            message = "Deck is empty."
            return message

        card_list = "\n".join(
            [f"{dc.quantity}x {dc.card.name} -- {dc.card.id}: {dc.card.llm_summary}" for dc in deck_cards]
        )
        message = f"Cards in deck:\n{card_list}"
        return message
    except Deck.DoesNotExist:
        message = f"Deck with ID {ctx.deps.deck_id} does not exist."
        return message


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
    response = await sync_to_async(validate_deck_basic)(ctx.deps.deck_id)
    return response
