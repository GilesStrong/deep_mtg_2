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

from pydantic import BaseModel, Field


class Memory(BaseModel):
    name: str = Field(
        max_length=64, description="The name of the memory, which can be used to reference it in future queries."
    )
    text: str = Field(description="The content of the memory, which can be any text that the agent wants to remember.")
    related_card_uuids: set[UUID] = Field(
        default_factory=set,
        max_length=10,
        description="A list of UUIDs of cards that are related to this memory, which can be used to link the memory to specific cards and retrieve it later based on those cards. Up to 10 related card UUIDs can be included.",
    )


class ExistingMemory(Memory):
    id: UUID = Field(
        description="The unique identifier of the memory in the database, used for referencing and updating the memory."
    )
    created_at: str = Field(
        description="The timestamp of when the memory was created in the database, used for tracking the age of the memory and determining if it may be obsolete or in need of consolidation with newer memories."
    )
