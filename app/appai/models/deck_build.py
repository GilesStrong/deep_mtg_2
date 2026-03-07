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

from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from appcards.models.deck import Deck
from django.db import models


class DeckBuildStatus(models.TextChoices):
    PENDING = 'PENDING'
    IN_PROGRESS = 'IN_PROGRESS'
    BUILDING_DECK = 'BUILDING_DECK'
    CLASSIFYING_DECK_CARDS = 'CLASSIFYING_DECK_CARDS'
    FINDING_REPLACEMENT_CARDS = 'FINDING_REPLACEMENT_CARDS'
    COMPLETED = 'COMPLETED'
    FAILED = 'FAILED'


class DeckBuildTask(models.Model):
    id = models.UUIDField(primary_key=True, editable=False, unique=True, default=uuid4)
    deck = models.ForeignKey(Deck, on_delete=models.CASCADE, related_name='build_tasks')
    status = models.CharField(max_length=50, choices=DeckBuildStatus.choices, default=DeckBuildStatus.PENDING)
    result = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    if TYPE_CHECKING:
        deck_id: UUID

    def __str__(self) -> str:
        return f"DeckBuildTask(id={self.id}, deck_id={self.deck_id}, status={self.status})"
