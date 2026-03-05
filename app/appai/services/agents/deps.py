from typing import Optional
from uuid import UUID

from appcards.constants.cards import CURRENT_STANDARD_SET_CODES
from pydantic import BaseModel, Field


class DeckBuildingDeps(BaseModel):
    deck_id: UUID = Field(..., description="The ID of the deck to modify")
    available_set_codes: set[str] = Field(
        default_factory=lambda: set(CURRENT_STANDARD_SET_CODES),
        description="The set codes that the deck is allowed to include cards from",
    )
    deck_description: str = Field(..., description="A natural language description of the desired deck")
    build_task_id: Optional[UUID] = Field(
        ..., description="The ID of the deck build task associated with this deck construction"
    )
