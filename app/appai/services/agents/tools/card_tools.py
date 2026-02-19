from uuid import UUID

from appcards.models import Card
from appcards.modules.card_info import CardInfo, card_to_info
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
    if isinstance(card_id, str):
        try:
            card = Card.objects.get(name=card_id)
        except Card.DoesNotExist:
            return f"Card with name '{card_id}' does not exist."
    else:
        try:
            card = Card.objects.get(id=card_id)
        except Card.DoesNotExist:
            return f"Card with ID {card_id} does not exist."

    return card_to_info(card)
