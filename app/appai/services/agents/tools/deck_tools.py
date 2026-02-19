import html
import unicodedata
from uuid import UUID

from appcards.models import Card, Deck
from appcards.models.deck import DeckCard, DeckValidationResult, validate_deck_basic
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
    print(f"Renaming deck ID {ctx.deps.deck_id} to '{new_name}'...")
    if new_name.strip() == "":
        message = "Deck name cannot be empty."
        print(message)
        return message
    try:
        deck = await Deck.objects.aget(id=ctx.deps.deck_id)
        deck.name = unicodedata.normalize("NFKC", html.escape(new_name))
        await deck.asave()
        message = f"Deck renamed to '{deck.name}'."
        print(message)
        return message
    except Deck.DoesNotExist:
        message = f"Deck with ID {ctx.deps.deck_id} does not exist."
        print(message)
        return message


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
    print(f"Adding {number_to_add}x card ID {card_id} to deck ID {ctx.deps.deck_id}...")
    try:
        deck = await Deck.objects.aget(id=ctx.deps.deck_id)
    except Deck.DoesNotExist:
        message = f"Deck with ID {ctx.deps.deck_id} does not exist."
        print(message)
        return message

    try:
        card = await Card.objects.aget(id=card_id)
    except Card.DoesNotExist:
        message = f"Card with ID {card_id} does not exist."
        print(message)
        return message

    deck_card, created = await DeckCard.objects.aget_or_create(deck=deck, card=card, defaults={'quantity': 0})
    deck_card.quantity += number_to_add
    await deck_card.asave()

    validation_result = await sync_to_async(validate_deck_basic)(deck)
    ctx.deps.validated = validation_result.valid

    total_cards = await DeckCard.objects.filter(deck=deck).aaggregate(Sum('quantity'))
    total_cards = total_cards['quantity__sum'] or 0
    message = f"Added {number_to_add}x '{card.name}' to deck '{deck.name}'. Deck now has {total_cards} total cards ({deck_card.quantity}x {card.name})."
    print(message)
    return message


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
    print(f"Removing {number_to_remove}x card ID {card_id} from deck ID {ctx.deps.deck_id}...")
    try:
        deck = await Deck.objects.aget(id=ctx.deps.deck_id)
    except Deck.DoesNotExist:
        message = f"Deck with ID {ctx.deps.deck_id} does not exist."
        print(message)
        return message

    try:
        card = await Card.objects.aget(id=card_id)
    except Card.DoesNotExist:
        message = f"Card with ID {card_id} does not exist."
        print(message)
        return message

    try:
        deck_card = await DeckCard.objects.aget(deck=deck, card=card)
    except DeckCard.DoesNotExist:
        message = f"Card '{card.name}' is not in deck '{deck.name}'."
        print(message)
        return message

    deck_card.quantity -= number_to_remove

    if deck_card.quantity <= 0:
        await deck_card.adelete()
        ctx.deps.validated = False
        total_cards = await DeckCard.objects.filter(deck=deck).aaggregate(Sum('quantity'))
        total_cards = total_cards['quantity__sum'] or 0
        message = (
            f"Removed all copies of '{card.name}' from deck '{deck.name}'. Deck now has {total_cards} total cards."
        )
        print(message)
        return message
    else:
        await deck_card.asave()
        validation_result = await sync_to_async(validate_deck_basic)(deck)
        ctx.deps.validated = validation_result.valid
        total_cards = await DeckCard.objects.filter(deck=deck).aaggregate(Sum('quantity'))
        total_cards = total_cards['quantity__sum'] or 0
        message = f"Removed {number_to_remove}x '{card.name}' from deck '{deck.name}'. Deck now has {total_cards} total cards ({deck_card.quantity}x {card.name} remaining)."
        print(message)
        return message


@beartype
async def clear_deck(ctx: RunContext[DeckBuildingDeps]) -> str:
    """
    Clears all cards from a deck.

    Returns:
        str: A message indicating the result of the operation.
    """
    print(f"Clearing all cards from deck ID {ctx.deps.deck_id}...")
    try:
        deck = await Deck.objects.aget(id=ctx.deps.deck_id)
    except Deck.DoesNotExist:
        message = f"Deck with ID {ctx.deps.deck_id} does not exist."
        print(message)
        return message

    await DeckCard.objects.filter(deck=deck).adelete()
    ctx.deps.validated = False
    message = f"All cards removed from deck '{deck.name}'."
    print(message)
    return message


@beartype
async def list_deck_cards(ctx: RunContext[DeckBuildingDeps]) -> str:
    """
    Lists all cards in a deck.

    Returns:
        str: A message listing all cards in the deck.
    """
    try:
        print(f"Listing cards for deck ID {ctx.deps.deck_id}...")

        deck_cards: list[DeckCard] = await sync_to_async(list)(  # type: ignore [call-arg]
            DeckCard.objects.filter(deck_id=ctx.deps.deck_id).select_related('card', 'deck')
        )

        if not deck_cards:
            message = "Deck is empty."
            print(message)
            return message

        card_list = "\n".join(
            [f"{dc.quantity}x {dc.card.name} -- {dc.card.id}: {dc.card.llm_summary}" for dc in deck_cards]
        )
        message = f"Cards in deck:\n{card_list}"
        print(message)
        return message
    except Deck.DoesNotExist:
        message = f"Deck with ID {ctx.deps.deck_id} does not exist."
        print(message)
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
    print(f"Validating deck ID {ctx.deps.deck_id}...")
    response = await sync_to_async(validate_deck_basic)(ctx.deps.deck_id)
    ctx.deps.validated = response.valid
    print(
        f"Deck validation result for deck ID {ctx.deps.deck_id}: valid={response.valid}, issues={response.issues}, total_cards={response.total_cards}"
    )
    return response
