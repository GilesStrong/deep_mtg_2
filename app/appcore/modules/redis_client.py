from functools import lru_cache

import redis
from app.app_settings import APP_SETTINGS


@lru_cache(maxsize=1)
def get_redis() -> redis.Redis:
    return redis.Redis.from_url(APP_SETTINGS.REDIS_URL, decode_responses=True)
