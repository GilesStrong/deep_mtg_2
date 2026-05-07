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

from appcore.modules.beartype import beartype
from asgiref.sync import sync_to_async

from appcards.models.card import Card


class CardValidationError(ValueError):
    pass


@beartype
async def check_related_card_uuids(card_ids: set[UUID]) -> None:
    """
    Checks if the given set of card UUIDs correspond to existing cards.
    Raises a CardValidationError if any of the UUIDs do not correspond to existing cards.

    Args:
        card_ids (set[UUID]): A set of UUIDs of cards to check for existence

    Raises:
        CardValidationError: If any of the UUIDs do not correspond to existing cards.

    Returns:
        None: If all UUIDs correspond to existing cards, the function returns None without raising an error.
    """
    if len(card_ids) == 0:
        return
    existing_card_uuids: set[UUID] = set(
        await sync_to_async(list)(Card.objects.filter(id__in=card_ids).values_list("id", flat=True))  # type: ignore [call-arg]
    )
    non_existing_uuids = card_ids - existing_card_uuids
    if len(non_existing_uuids) > 0:
        raise CardValidationError(
            f"The following related_card_uuids do not correspond to existing cards: {', '.join(str(uuid) for uuid in non_existing_uuids)}"
        )
