from uuid import UUID

from appcards.models.deck import Deck
from ninja import Field, Schema
from ninja.errors import HttpError
from pydantic import field_validator

from appai.models.deck_build import DeckBuildTask

PROMPT_LENGTH = (20, 3000)


class CheckQuotaOut(Schema):
    remaining: int = Field(..., description="The number of remaining deck builds the user can perform today.")


class BuildDeckStatusesOut(Schema):
    all: list[str] = Field(..., description="All possible deck build status values.")
    pollable: list[str] = Field(
        ..., description="Deck build status values that indicate an active in-progress build and should be polled."
    )


class BuildDeckPostIn(Schema):
    prompt: str = Field(
        ...,
        description='The prompt for building the deck. This should include the desired theme, strategy, or specific cards you want in the deck.',
        min_length=PROMPT_LENGTH[0],
        max_length=PROMPT_LENGTH[1],
    )
    set_codes: list[str] | None = Field(
        None, description='Optional list of set codes to restrict the card selection to specific sets.'
    )
    deck_id: UUID | None = Field(
        None, description='Optional deck ID to update an existing deck instead of creating a new one.'
    )

    @field_validator('deck_id', mode='after')
    @classmethod
    def validate_deck_id(cls, value: UUID | None) -> UUID | None:
        if value is None:
            return None
        if not Deck.objects.filter(id=value).exists():
            raise HttpError(404, 'Deck not found')
        return value

    @field_validator('set_codes', mode='after')
    @classmethod
    def validate_set_codes(cls, value: list[str] | None) -> list[str] | None:
        if value is not None and len(value) == 0:
            raise HttpError(400, 'Set codes list cannot be empty')
        return value


class BuildDeckPostOut(Schema):
    task_id: UUID
    status_url: str
    deck_id: UUID

    @field_validator('deck_id', mode='after')
    @classmethod
    def validate_deck_id(cls, value: UUID) -> UUID:
        if not Deck.objects.filter(id=value).exists():
            raise RuntimeError('Deck not found')
        return value

    @field_validator('task_id', mode='after')
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

    @field_validator('deck_id', mode='after')
    @classmethod
    def validate_deck_id(cls, value: UUID) -> UUID:
        if not Deck.objects.filter(id=value).exists():
            raise RuntimeError('Deck not found')
        return value
