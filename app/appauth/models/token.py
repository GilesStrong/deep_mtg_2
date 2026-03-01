import secrets
from datetime import timedelta
from hashlib import sha256
from typing import Self

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

    @staticmethod
    def hash_token(raw_token: str) -> str:
        """
        Hashes a raw token string using the SHA-256 algorithm.

        Args:
            raw_token (str): The raw token string to be hashed.

        Returns:
            str: The hexadecimal representation of the SHA-256 hash of the raw token.
        """
        return sha256(raw_token.encode("utf-8")).hexdigest()

    @classmethod
    def mint(cls, user: User, *, user_agent: str = "", ip: str | None = None) -> tuple["RefreshToken", str]:
        """
        Create and store a new refresh token for the given user.

        This class method generates a cryptographically secure random token,
        hashes it for storage, and persists a new ``RefreshToken`` record with
        an expiry calculated from ``APP_SETTINGS.REFRESH_TOKEN_TTL_SECONDS``.

        Args:
            user (User): The authenticated user for whom the token is minted.
            user_agent (str, optional): The client's User-Agent string. Truncated
                to 1000 characters. Defaults to an empty string.
            ip (str | None, optional): The client's IP address. Defaults to None.

        Returns:
            tuple[RefreshToken, str]: A two-element tuple containing:
                - The newly created ``RefreshToken`` database record.
                - The raw (unhashed) token string to be delivered to the client.

        Note:
            Only the hashed version of the token is stored in the database.
            The raw token is returned exactly once and cannot be recovered later.
        """
        now = timezone.now()
        raw_token = secrets.token_urlsafe(48)
        record = cls.objects.create(
            user=user,
            token=cls.hash_token(raw_token),
            expires_at=now + timedelta(seconds=APP_SETTINGS.REFRESH_TOKEN_TTL_SECONDS),
            user_agent=user_agent[:1000],
            ip=ip,
        )
        return record, raw_token

    @classmethod
    def from_raw_token(cls, raw_token: str) -> Self:
        """
        Retrieve a RefreshToken instance by searching with either a hashed or raw token value.

        This class method first attempts to find a token by its hashed value. If no match
        is found, it falls back to searching with the raw token string directly.
        The returned instance will have its related user pre-fetched via select_related.

        Args:
            raw_token (str): The raw (unhashed) token string to search for.

        Returns:
            RefreshToken: The RefreshToken instance associated with the given token,
                          with the related user pre-fetched.

        Raises:
            cls.DoesNotExist: If no matching token is found using either the hashed
                              or raw token value.
        """
        token_hash = cls.hash_token(raw_token)
        try:
            return cls.objects.select_related("user").get(token=token_hash)
        except cls.DoesNotExist:
            return cls.objects.select_related("user").get(token=raw_token)

    def is_valid(self) -> bool:
        """
        Check if the token is valid.

        A token is considered valid if it has not been revoked and has not expired.

        Returns:
            bool: True if the token is valid, False otherwise.
                - Returns False if the token has been revoked (revoked_at is not None).
                - Returns True if the current time is before the token's expiration time.
                - Returns False if the token has expired.
        """
        if self.revoked_at is not None:
            return False
        return timezone.now() < self.expires_at
