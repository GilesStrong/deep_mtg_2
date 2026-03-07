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

from uuid import UUID

import logfire
from aiocache import cached
from appcards.models import Card
from appcards.modules.card_info import CardInfo, card_to_info
from appcore.modules.beartype import beartype
from asgiref.sync import sync_to_async


@cached(ttl=3600)  # Cache for 1 hour
@beartype
async def inspect_card(card_id: UUID) -> CardInfo | str:
    """
    Retrieves details about a card.

    Args:
        card_id (UUID): The ID of the card to inspect.

    Returns:
        CardInfo|str: A description of the card, or an error message if not found.
    """
    if isinstance(card_id, str):
        try:
            card = await Card.objects.aget(name=card_id)
        except Card.DoesNotExist:
            message = f"Card with name '{card_id}' does not exist."
            logfire.warning(message)
            return message
    else:
        try:
            card = await Card.objects.aget(id=card_id)
        except Card.DoesNotExist:
            message = f"Card with ID {card_id} does not exist."
            logfire.warning(message)
            return message

    card_info = await sync_to_async(card_to_info)(card)
    return card_info
