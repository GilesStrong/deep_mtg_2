from appcards.constants.cards import CARD_TAGS
from appcards.models.card import ManaColorEnum
from ninja import Field, Schema
from ninja.errors import HttpError
from pydantic import field_validator

PROMPT_LENGTH = (20, 200)


class SearchCardsIn(Schema):
    query: str = Field(
        ...,
        description='The search query for finding cards. This should include keywords, card names, or other relevant information to help identify the desired cards.',
        min_length=PROMPT_LENGTH[0],
        max_length=PROMPT_LENGTH[1],
    )
    tags: list[str] = Field(
        default_factory=list, description='Optional list of tags to filter the card search results.'
    )
    set_codes: list[str] = Field(
        default_factory=list,
        description='Optional list of set codes to filter the card search results.',
    )
    colors: list[ManaColorEnum] = Field(
        default_factory=list,
        description='Optional list of colors to filter the card search results. Colors should be represented by their single-letter codes (e.g., "W" for white, "U" for blue, "B" for black, "R" for red, "G" for green).',
    )

    @field_validator('tags', mode='before')
    @classmethod
    def validate_tags(cls, value: list[str]) -> list[str]:
        if not isinstance(value, list):
            raise ValueError('Tags must be a list of strings')
        set_value = set(value)
        invalid_tags = set_value - set(CARD_TAGS.keys())
        if len(invalid_tags):
            raise HttpError(
                400, f'Invalid tags: {", ".join(invalid_tags)}. Valid tags are: {", ".join(CARD_TAGS.keys())}'
            )
        return value
