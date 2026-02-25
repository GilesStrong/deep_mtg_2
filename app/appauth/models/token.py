import secrets
from datetime import timedelta

from app.app_settings import APP_SETTINGS
from appuser.models import User
from django.db import models
from django.utils import timezone


class RefreshToken(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="refresh_tokens")
    token = models.CharField(max_length=128, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    revoked_at = models.DateTimeField(null=True, blank=True)
    user_agent = models.TextField(blank=True, default="")
    ip = models.GenericIPAddressField(null=True, blank=True)

    @classmethod
    def mint(cls, user: User, *, user_agent: str = "", ip: str | None = None) -> "RefreshToken":
        now = timezone.now()
        return cls.objects.create(
            user=user,
            token=secrets.token_urlsafe(48),
            expires_at=now + timedelta(seconds=APP_SETTINGS.REFRESH_TOKEN_TTL_SECONDS),
            user_agent=user_agent[:1000],
            ip=ip,
        )

    def is_valid(self) -> bool:
        if self.revoked_at is not None:
            return False
        return timezone.now() < self.expires_at
