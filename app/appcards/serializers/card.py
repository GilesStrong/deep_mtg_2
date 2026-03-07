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

from typing import TYPE_CHECKING
from uuid import UUID

from ninja import Field, Schema
from ninja.errors import HttpError

from appcards.models.card import Card


class SetCodesOut(Schema):
    set_codes: list[str] = Field(
        ..., description="A list of all available set codes that can be used for deck construction"
    )


class SetTagsOut(Schema):
    tags: dict[str, dict[str, str]] = Field(
        ...,
        description="A hierarchical dictionary of all available tags that can be used for deck construction, where the keys are primary tags and the values are dictionaries of subtags and their descriptions",
    )


class GetCardIn(Schema):
    card_id: UUID = Field(..., description='The unique identifier of the card to retrieve.')

    if TYPE_CHECKING:
        _card_cache: Card

    @property
    def card(self) -> Card:
        if not hasattr(self, '_card_cache'):
            try:
                object.__setattr__(self, '_card_cache', Card.objects.get(id=self.card_id))
            except Card.DoesNotExist:
                raise HttpError(404, f"Card with ID {self.card_id} not found")
        return self._card_cache
