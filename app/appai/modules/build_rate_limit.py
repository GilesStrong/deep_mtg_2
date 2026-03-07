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

from __future__ import annotations

from datetime import datetime, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

import redis
from app.app_settings import APP_SETTINGS
from appcore.modules.beartype import beartype
from pydantic import BaseModel, ConfigDict

LOCAL_TIMEZONE = ZoneInfo(APP_SETTINGS.LOCALITY)


class LimitResult(BaseModel):
    model_config = ConfigDict(frozen=True)
    allowed: bool
    remaining: int
    retry_after_seconds: int
    limit: int
    reset_at: datetime


@beartype
def _seconds_until_local_midnight(now: datetime) -> int:
    """
    Calculate the number of seconds from a given datetime until the next midnight in local time.

    Args:
        now (datetime): A timezone-aware datetime object representing the current time.

    Returns:
        int: The number of seconds until the next local midnight. Returns at least 1 second
            to avoid zero or negative values.
    """
    # now must be tz-aware
    tomorrow = (now + timedelta(days=1)).date()
    midnight = datetime.combine(tomorrow, datetime.min.time(), tzinfo=LOCAL_TIMEZONE)
    return max(1, int((midnight - now).total_seconds()))


@beartype
def check_remaining_daily_quota(
    redis_client: redis.Redis,
    user_id: UUID,
) -> LimitResult:
    """
    Check whether a user has remaining daily quota without consuming it.

    Reads the current Redis counter for today's key and returns the same quota
    metadata shape as ``withdraw_from_daily_quota``, but does not increment the
    counter.

    Args:
        rredis_client (redis.Redis): An active Redis client instance used for quota tracking.
        user_id (UUID): The unique identifier of the user whose quota is being checked.

    Returns:
        LimitResult: A dataclass containing:
            - allowed (bool): Whether the user is permitted to perform another deck build.
            - remaining (int): The number of deck builds still available today.
            - retry_after_seconds (int): Seconds to wait before retrying if blocked;
            0 if the request would be allowed.
            - limit (int): The maximum number of deck builds allowed per day.
            - reset_at (datetime): The datetime at which the quota will reset.
    """
    now = datetime.now(LOCAL_TIMEZONE)
    day = now.strftime("%Y%m%d")
    key = f"quota:deckbuild:{user_id}:{day}"

    raw_count = redis_client.get(key)
    try:
        count = int(raw_count) if raw_count is not None else 0  # type: ignore[arg-type]
    except (TypeError, ValueError):
        count = 0

    limit = APP_SETTINGS.DECK_BUILDS_PER_DAY
    remaining = max(0, limit - count)
    allowed = count < limit

    ttl = _seconds_until_local_midnight(now)
    reset_at = now + timedelta(seconds=ttl)
    retry_after = 0 if allowed else ttl

    return LimitResult(
        allowed=allowed,
        remaining=remaining,
        retry_after_seconds=retry_after,
        limit=limit,
        reset_at=reset_at,
    )


@beartype
def withdraw_from_daily_quota(
    redis_client: redis.Redis,
    user_id: UUID,
) -> LimitResult:
    """
    Check and enforce the daily deck-building quota for a given user.

    Uses Redis to track the number of deck builds performed by the user on the
    current calendar day (keyed by local midnight as the day boundary). The counter
    is atomically incremented on each call, and a TTL is set to expire the key at
    the next local midnight, ensuring the quota resets daily.

    Args:
        redis_client (redis.Redis): An active Redis client instance used for quota tracking.
        user_id (UUID): The unique identifier of the user whose quota is being checked.

    Returns:
        LimitResult: A dataclass containing:
            - allowed (bool): Whether the user is permitted to perform another deck build.
            - remaining (int): The number of deck builds still available today.
            - retry_after_seconds (int): Seconds to wait before retrying if blocked;
            0 if the request is allowed.
            - limit (int): The maximum number of deck builds allowed per day.
            - reset_at (datetime): The datetime at which the quota will reset.

    Notes:
        - The quota limit is read from ``APP_SETTINGS.DECK_BUILDS_PER_DAY``.
        - If the Redis key loses its TTL unexpectedly, it will be restored on the
        next call to prevent a permanently persisted key.
        - The day boundary is determined by local midnight (``LOCAL_TIMEZONE``).
    """
    now = datetime.now(LOCAL_TIMEZONE)
    day = now.strftime("%Y%m%d")
    key = f"quota:deckbuild:{user_id}:{day}"

    ttl = _seconds_until_local_midnight(now)

    # Atomic-ish pattern: INCR then ensure expiry exists
    count = int(redis_client.incr(key))  # type: ignore[arg-type]
    if count == 1:  # First entry for the day, set the TTL
        redis_client.expire(key, ttl)
    else:
        # If key somehow lost TTL, restore it
        if redis_client.ttl(key) == -1:
            redis_client.expire(key, ttl)

    remaining = max(0, APP_SETTINGS.DECK_BUILDS_PER_DAY - count)
    allowed = count <= APP_SETTINGS.DECK_BUILDS_PER_DAY

    reset_at = now + timedelta(seconds=ttl)
    retry_after = 0 if allowed else ttl  # blocked until reset

    return LimitResult(
        allowed=allowed,
        remaining=remaining if allowed else 0,
        retry_after_seconds=retry_after,
        limit=APP_SETTINGS.DECK_BUILDS_PER_DAY,
        reset_at=reset_at,
    )
