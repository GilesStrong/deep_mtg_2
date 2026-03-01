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
        description="A hierachical dictionary of all available tags that can be used for deck construction, where the keys are primary tags and the values are dictionaries of subtags and their descriptions",
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
