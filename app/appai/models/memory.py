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

from typing import Any
from uuid import uuid4

from appcards.models.card import Card
from appsearch.services.qdrant.client import QDRANT_CLIENT
from django.db import models

from appai.constants.storage import MEMORY_COLLECTION_NAME


class Memory(models.Model):
    id = models.UUIDField(default=uuid4, editable=False, primary_key=True, unique=True)
    name = models.CharField(max_length=64, blank=False, null=False)
    text = models.TextField(blank=False, null=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    related_cards = models.ManyToManyField(Card, blank=True)

    def __str__(self) -> str:
        return f"Memory(id={self.id}, name={self.name})"

    def delete(self, *args: Any, **kwargs: Any) -> tuple[int, dict[str, int]]:
        # Delete the memory from the vector database
        QDRANT_CLIENT.delete(collection_name=MEMORY_COLLECTION_NAME, points_selector=[str(self.id)])
        return super().delete(*args, **kwargs)
