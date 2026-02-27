from uuid import uuid4

from django.db import models


class User(models.Model):
    id = models.UUIDField(default=uuid4, editable=False, primary_key=True, unique=True)
    google_id = models.CharField(max_length=255, unique=True)
    verified = models.BooleanField(default=False)
    warning_count = models.IntegerField(default=0)
