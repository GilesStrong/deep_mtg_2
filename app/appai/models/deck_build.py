from uuid import uuid4

from django.db import models


class DeckBuildStatus(models.TextChoices):
    PENDING = 'pending', 'Pending'
    IN_PROGRESS = 'in_progress', 'In Progress'
    COMPLETED = 'completed', 'Completed'
    FAILED = 'failed', 'Failed'


class DeckBuildTask(models.Model):
    id = models.UUIDField(primary_key=True, editable=False, unique=True, default=uuid4)
    task_id = models.CharField(max_length=255, unique=True, editable=False)
    deck_id = models.UUIDField()
    status = models.CharField(max_length=50, choices=DeckBuildStatus.choices, default=DeckBuildStatus.PENDING)
    result = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"DeckBuildTask(task_id={self.task_id}, deck_id={self.deck_id}, status={self.status})"
