import uuid

from django.db import models


class Printing(models.Model):
    id = models.UUIDField(auto_created=True, editable=False, unique=True, primary_key=True, default=uuid.uuid4)
    card = models.ForeignKey('Card', on_delete=models.CASCADE, related_name='printings')
    set_code = models.CharField(max_length=10)

    class Meta:
        unique_together = ('card', 'set_code')

    def __str__(self) -> str:
        return f"{self.card.name} - {self.set_code}"
