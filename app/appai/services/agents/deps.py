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
    memories_written: int = Field(
        0, description="The number of memories that have been written to during this deck construction process"
    )
    checked_memories: bool = Field(
        False,
        description="If the agent attempts to return the output and has not written any memories, and this is false, then the output will be rejected, and this will be se to true. This is to remind the agent to save memories of its thought process, which can be used to improve future iterations of the deck construction process. If the agent attempts to return the output and has not written any memories, and this is true, then the output will be accepted, but a warning will be logged. This is to allow the agent to bypass the memory-writing requirement if it determines that it is not necessary, while still encouraging it to save memories in most cases.",
    )
    memory_searches: int = Field(
        0, description="The number of times the agent has searched for memories during this deck construction process"
    )
