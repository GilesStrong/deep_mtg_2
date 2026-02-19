from uuid import UUID

from appcards.constants.cards import CURRENT_STANDARD_SET_CODES
from pydantic import BaseModel, Field


class DeckBuildingDeps(BaseModel):
    deck_id: UUID = Field(..., description="The ID of the deck to modify")
    available_set_codes: set[str] = Field(
        default=CURRENT_STANDARD_SET_CODES, description="The set codes that the deck is allowed to include cards from"
    )
    validated: bool = Field(False, description="Whether the current state of the deck has been validated for legality")
