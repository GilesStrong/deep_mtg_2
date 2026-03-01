from __future__ import annotations

import time
from dataclasses import dataclass

import redis
from appcore.modules.redis_client import get_redis
from django.http import HttpRequest


@dataclass(frozen=True)
class AuthRateLimitResult:
    allowed: bool
    retry_after_seconds: int


def _extract_client_ip(request: HttpRequest) -> str:
    """
    Extract the client's IP address from an HTTP request.

    This function attempts to determine the real client IP address by first
    checking the 'X-Forwarded-For' header (used when the request passes through
    proxies or load balancers), and falling back to the 'REMOTE_ADDR' metadata
    if the header is not present.

    Args:
        request (HttpRequest): The incoming Django HTTP request object.

    Returns:
        str: The client's IP address as a string. Returns the first IP from the
             'X-Forwarded-For' header if available, otherwise returns the
             'REMOTE_ADDR' value. Returns 'unknown' if neither source provides
             a valid IP address.

    Notes:
        - When multiple IPs are present in 'X-Forwarded-For', only the first
          (leftmost) IP address is returned, which represents the original client.
        - Be aware that 'X-Forwarded-For' headers can be spoofed by clients,
          so this should not be used for security-critical IP validation.
    """
    forwarded_for = request.headers.get("X-Forwarded-For", "")
    if forwarded_for:
        first_hop = forwarded_for.split(",")[0].strip()
        if first_hop:
            return first_hop
    remote_addr = request.META.get("REMOTE_ADDR", "")
    return remote_addr or "unknown"


def check_auth_rate_limit(
    request: HttpRequest, *, action: str, limit: int, window_seconds: int = 60
) -> AuthRateLimitResult:
    """
    Check whether an authentication action is within its rate limit for the requesting client.

    Evaluates a sliding-window rate limit backed by Redis. Each unique combination of
    action type and client IP address is tracked in a dedicated Redis key that expires
    after the configured window.

    Args:
        request (HttpRequest): The incoming Django HTTP request used to extract the
            client's IP address.
        action (str): A string identifier for the action being rate-limited
            (e.g. ``"login"``, ``"password_reset"``).
        limit (int): Maximum number of allowed attempts within the time window.
            A value of ``0`` or less unconditionally blocks the request.
        window_seconds (int, optional): Duration of the rate-limit window in seconds.
            Defaults to ``60``.

    Returns:
        AuthRateLimitResult: A result object with two fields:

            * ``allowed`` (bool) – ``True`` if the request is within the limit,
              ``False`` if the limit has been exceeded or ``limit <= 0``.
            * ``retry_after_seconds`` (int) – Suggested number of seconds the caller
              should wait before retrying. Equals the remaining TTL of the Redis key
              when the limit is exceeded, or ``0`` when the request is allowed.

    Raises:
        None: All ``redis.RedisError`` exceptions are caught internally. When Redis
            is unavailable the function fails open, returning
            ``AuthRateLimitResult(allowed=True, retry_after_seconds=0)``.

    Notes:
        * The Redis key is namespaced as ``rate:auth:<action>:<client_ip>:<bucket>``
          where ``bucket`` is derived by floor-dividing the current epoch time by
          ``window_seconds``, creating a fixed-window counter.
        * The TTL is set only on the first increment (``count == 1``) to avoid
          resetting the window on every request.
    """
    if limit <= 0:
        return AuthRateLimitResult(allowed=False, retry_after_seconds=window_seconds)

    client_ip = _extract_client_ip(request)
    bucket = time.time() // window_seconds
    key = f"rate:auth:{action}:{client_ip}:{int(bucket)}"

    try:
        redis_client = get_redis()
        count = int(redis_client.incr(key))  # type: ignore[arg-type]
        if count == 1:
            redis_client.expire(key, window_seconds)
        ttl = int(redis_client.ttl(key))  # type: ignore[arg-type]
        retry_after = ttl if ttl > 0 else window_seconds
        return AuthRateLimitResult(allowed=count <= limit, retry_after_seconds=retry_after)
    except redis.RedisError:
        return AuthRateLimitResult(allowed=True, retry_after_seconds=0)
