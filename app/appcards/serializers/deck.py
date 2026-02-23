from typing import TYPE_CHECKING
from uuid import UUID

from ninja import Field, Schema
from ninja.errors import HttpError
from pydantic import field_validator

from appcards.models.card import Card
from appcards.models.deck import Deck
from appcards.modules.card_info import CardInfo


class GetDeckIn(Schema):
    deck_id: UUID = Field(..., description='The unique identifier of the deck to retrieve.')

    if TYPE_CHECKING:
        _deck_cache: Deck

    @property
    def deck(self) -> Deck:
        if not hasattr(self, '_deck_cache'):
            try:
                object.__setattr__(self, '_deck_cache', Deck.objects.get(id=self.deck_id))
            except Deck.DoesNotExist:
                raise HttpError(404, f"Deck with ID {self.deck_id} not found")
        return self._deck_cache


class GetSummaryDeckOut(Schema):
    id: UUID
    name: str
    short_summary: str | None
    set_codes: list[str]
    date_updated: str
    generation_status: str | None = None
    generation_task_id: UUID | None = None

    @field_validator('id', mode='before')
    @classmethod
    def validate_id(cls, value: UUID) -> UUID:
        if not Deck.objects.filter(id=value).exists():
            raise RuntimeError('Deck not found')
        return value


class GetFullDeckOut(Schema):
    id: UUID
    name: str
    short_summary: str | None
    full_summary: str | None
    set_codes: list[str]
    date_updated: str
    cards: list[tuple[int, CardInfo]]

    @field_validator('id', mode='before')
    @classmethod
    def validate_id(cls, value: UUID) -> UUID:
        if not Deck.objects.filter(id=value).exists():
            raise RuntimeError('Deck not found')
        return value

    @field_validator('cards', mode='before')
    @classmethod
    def validate_cards(cls, value: list[tuple[int, CardInfo]]) -> list[tuple[int, CardInfo]]:
        card_ids = set()
        for quantity, card_info in value:
            if quantity < 1:
                raise RuntimeError('Invalid card quantity')
            card_ids.add(card_info.id)

        if not Card.objects.filter(id__in=card_ids).count() == len(card_ids):
            raise RuntimeError('One or more cards not found')
        return value
