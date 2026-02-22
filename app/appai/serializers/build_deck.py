from uuid import UUID

from appcards.models.deck import Deck
from ninja import Field, Schema
from ninja.errors import HttpError
from pydantic import field_validator

from appai.models.deck_build import DeckBuildTask


class BuildDeckPostIn(Schema):
    prompt: str = Field(
        ...,
        description='The prompt for building the deck. This should include the desired theme, strategy, or specific cards you want in the deck.',
    )
    set_codes: list[str] | None = Field(
        None, description='Optional list of set codes to restrict the card selection to specific sets.'
    )
    deck_id: UUID | None = Field(
        None, description='Optional deck ID to update an existing deck instead of creating a new one.'
    )

    @field_validator('deck_id', mode='before')
    @classmethod
    def validate_deck_id(cls, value: UUID | None) -> UUID | None:
        if value is None:
            return None
        if not Deck.objects.filter(id=value).exists():
            raise HttpError(404, 'Deck not found')
        return value


class BuildDeckPostOut(Schema):
    task_id: UUID
    status_url: str
    deck_id: UUID

    @field_validator('deck_id', mode='before')
    @classmethod
    def validate_deck_id(cls, value: UUID) -> UUID:
        if not Deck.objects.filter(id=value).exists():
            raise RuntimeError('Deck not found')
        return value

    @field_validator('task_id', mode='before')
    @classmethod
    def validate_task_id(cls, value: UUID) -> UUID:
        if not DeckBuildTask.objects.filter(id=value).exists():
            raise RuntimeError('Deck build task not found')
        return value


class BuildDeckStatusIn(Schema):
    task_id: UUID


class BuildDeckStatusOut(Schema):
    status: str
    deck_id: UUID

    @field_validator('deck_id', mode='before')
    @classmethod
    def validate_deck_id(cls, value: UUID) -> UUID:
        if not Deck.objects.filter(id=value).exists():
            raise RuntimeError('Deck not found')
        return value
