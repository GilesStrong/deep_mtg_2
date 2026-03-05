from uuid import uuid4

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

    def __str__(self) -> str:
        return f"DeckBuildTask(id={self.id}, deck_id={self.deck.id}, status={self.status})"
