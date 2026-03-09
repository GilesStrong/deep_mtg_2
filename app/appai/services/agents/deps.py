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

from appcards.constants.cards import CURRENT_STANDARD_SET_CODES
from pydantic import BaseModel, Field


class DeckBuildingDeps(BaseModel):
    deck_id: UUID = Field(..., description="The ID of the deck to modify")
    available_set_codes: set[str] = Field(
        default_factory=lambda: set(CURRENT_STANDARD_SET_CODES),
        description="The set codes that the deck is allowed to include cards from",
    )
    deck_description: str = Field(..., description="A natural language description of the desired deck")
    build_task_id: UUID = Field(..., description="The ID of the deck build task associated with this deck construction")
