from uuid import UUID

from appcards.models import Card
from appcards.modules.card_info import CardInfo, card_to_info
from asgiref.sync import sync_to_async
from beartype import beartype


@beartype
async def inspect_card(card_id: UUID | str) -> CardInfo | str:
    """
    Retrieves details about a card.

    Args:
        card_id (UUID|str): The ID or exact name of the card to inspect.

    Returns:
        CardInfo|str: A description of the card, or an error message if not found.
    """
    print(f"Inspecting card ID {card_id}...")
    if isinstance(card_id, str):
        try:
            card = await Card.objects.aget(name=card_id)
        except Card.DoesNotExist:
            message = f"Card with name '{card_id}' does not exist."
            print(message)
            return message
    else:
        try:
            card = await Card.objects.aget(id=card_id)
        except Card.DoesNotExist:
            message = f"Card with ID {card_id} does not exist."
            print(message)
            return message

    card_info = await sync_to_async(card_to_info)(card)
    print(f"Card info for ID {card_id} found")
    return card_info
